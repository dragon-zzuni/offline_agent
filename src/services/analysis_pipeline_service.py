# -*- coding: utf-8 -*-
"""
메시지 분석 파이프라인 서비스

메시지 수집 → 우선순위 분류 → 요약 → 액션 추출 플로우를 담당하는 서비스입니다.
기존 main.py의 SmartAssistant 분석 로직을 재사용 가능한 서비스로 추출했습니다.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# TODO 중복 제거 서비스 import
try:
    from services.todo_deduplication_service import TodoDeduplicationService
    DEDUPLICATION_AVAILABLE = True
except ImportError:
    logger.warning("TodoDeduplicationService를 import할 수 없습니다. 중복 제거 기능이 비활성화됩니다.")
    DEDUPLICATION_AVAILABLE = False


class AnalysisPipelineService:
    """메시지 분석 파이프라인 서비스
    
    메시지 수집부터 TODO 생성까지의 전체 분석 플로우를 관리합니다.
    SmartAssistant의 분석 로직을 서비스로 추출하여 재사용성을 높였습니다.
    """
    
    def __init__(
        self,
        data_source_manager,
        priority_ranker,
        summarizer,
        action_extractor,
        user_profile: Optional[Dict[str, Any]] = None,
        top3_service=None,
        todo_repository=None
    ):
        """
        Args:
            data_source_manager: DataSourceManager 인스턴스
            priority_ranker: PriorityRanker 인스턴스
            summarizer: MessageSummarizer 인스턴스
            action_extractor: ActionExtractor 인스턴스
            user_profile: 사용자 프로필 정보 (email_address 등)
            top3_service: Top3Service 인스턴스 (선택사항, LLM 자동 선정용)
            todo_repository: TodoRepository 인스턴스 (선택사항, 중복 제거용)
        """
        self._data_source_manager = data_source_manager
        self._priority_ranker = priority_ranker
        self._summarizer = summarizer
        self._action_extractor = action_extractor
        self._user_profile = user_profile or {}
        self._top3_service = top3_service
        self._todo_repository = todo_repository
        
        # TODO 중복 제거 서비스 초기화
        if DEDUPLICATION_AVAILABLE:
            self._deduplication_service = TodoDeduplicationService()
            logger.info("✅ TodoDeduplicationService 초기화 완료")
        else:
            self._deduplication_service = None
            logger.warning("⚠️ TodoDeduplicationService 비활성화")
        
        # 통계
        self._stats = {
            "total_messages_analyzed": 0,
            "todos_created": 0,
            "todos_prevented": 0,
            "extraction_rate": 0.0
        }
        
        if top3_service:
            logger.info("✅ AnalysisPipelineService 초기화 완료 (Top3 자동 선정 활성화)")
        else:
            logger.info("✅ AnalysisPipelineService 초기화 완료")
    
    def set_user_profile(self, user_profile: Dict[str, Any]) -> None:
        """사용자 프로필 설정"""
        self._user_profile = user_profile
        logger.debug(f"사용자 프로필 업데이트: {user_profile.get('name', 'Unknown')}")
    
    async def analyze_messages(
        self,
        persona_id: str,
        time_range_start: Optional[datetime] = None,
        time_range_end: Optional[datetime] = None,
        top_n: int = 50,
        email_limit: Optional[int] = None,
        messenger_limit: Optional[int] = None,
        overall_limit: Optional[int] = None,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """
        메시지 분석 파이프라인 실행
        
        Args:
            persona_id: 페르소나 식별자 (mailbox 또는 handle)
            time_range_start: 시작 시간
            time_range_end: 종료 시간
            top_n: 상세 분석할 상위 메시지 개수 (기본값: 50)
            email_limit: 이메일 최대 개수
            messenger_limit: 메신저 최대 개수
            overall_limit: 전체 메시지 최대 개수
            force_reload: 강제 리로드 여부
        
        Returns:
            {
                "todo_list": [...],
                "messages": [...],
                "analysis_results": [...],
                "summary": {
                    "total_messages": int,
                    "email_count": int,
                    "chat_count": int,
                    "todo_count": int,
                    "high_priority_count": int,
                    "medium_priority_count": int,
                    "low_priority_count": int
                },
                "conversation_summary": {...},
                "analysis_report_text": str
            }
        """
        logger.info(f"🚀 분석 파이프라인 시작 (페르소나: {persona_id})")
        
        # 1. 메시지 수집
        messages = await self._collect_messages(
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            email_limit=email_limit,
            messenger_limit=messenger_limit,
            overall_limit=overall_limit,
            force_reload=force_reload
        )
        
        if not messages:
            logger.warning("수집된 메시지가 없습니다.")
            return self._empty_result()
        
        # 2. 우선순위 분류
        ranked_messages = await self._rank_messages(messages)
        
        # 3. 상위 N개 요약
        top_messages = [m for (m, _) in ranked_messages][:top_n]
        summaries = await self._summarize_messages(top_messages)
        
        # 4. 액션 추출
        actions = await self._extract_actions(top_messages)
        
        # 5. 결과 병합
        analysis_results = self._merge_results(
            ranked_messages=ranked_messages,
            summaries=summaries,
            actions=actions
        )
        
        # 6. TODO 리스트 생성 (persona_name 전달)
        persona_name = self._user_profile.get("name") or persona_id
        todo_list = self._generate_todo_list(analysis_results, persona_name=persona_name)
        
        # 통계 업데이트
        self._stats["total_messages_analyzed"] = len(messages)
        
        # 7. 전체 대화 요약 (메시지가 50개 이하일 때만)
        conversation_summary = None
        if len(messages) <= 50:
            conversation_summary = await self._summarize_conversation(messages)
        else:
            logger.info(f"메시지가 {len(messages)}개로 많아 전체 대화 요약을 스킵합니다.")
        
        # 8. 분석 리포트 텍스트 생성
        analysis_report_text = await self._build_analysis_report(
            analysis_results=analysis_results,
            conversation_summary=conversation_summary
        )
        
        # 9. 통계 계산
        summary = self._calculate_summary(
            messages=messages,
            todo_list=todo_list,
            analysis_results=analysis_results
        )
        
        logger.info(f"✅ 분석 파이프라인 완료 (메시지: {len(messages)}개, TODO: {len(todo_list)}개)")
        
        # 10. 자연어 규칙이 있으면 자동으로 LLM Top3 선정 (선택적)
        # Top3Service가 주입되어 있고, 자연어 규칙이 설정되어 있으면 실행
        if hasattr(self, '_top3_service') and self._top3_service:
            try:
                last_instruction = self._top3_service.get_last_instruction()
                if last_instruction and last_instruction.strip():
                    logger.info(f"[Pipeline] 자연어 규칙 감지, LLM Top3 자동 선정 시작")
                    logger.debug(f"[Pipeline] 규칙: {last_instruction[:100]}")
                    
                    # LLM으로 Top3 선정
                    top3_ids = self._top3_service.pick_top3(todo_list)
                    
                    if top3_ids:
                        logger.info(f"[Pipeline] ✅ LLM Top3 자동 선정 완료: {len(top3_ids)}개")
                        # TODO 리스트에 is_top3 플래그 추가
                        for todo in todo_list:
                            todo["is_top3"] = todo.get("id") in top3_ids
                    else:
                        logger.warning("[Pipeline] LLM Top3 선정 결과가 비어있습니다")
            except Exception as e:
                logger.error(f"[Pipeline] LLM Top3 자동 선정 실패: {e}")
                import traceback
                logger.debug(traceback.format_exc())
        
        return {
            "todo_list": todo_list,
            "messages": messages,
            "analysis_results": analysis_results,
            "summary": summary,
            "conversation_summary": conversation_summary,
            "analysis_report_text": analysis_report_text
        }
    
    async def _collect_messages(
        self,
        time_range_start: Optional[datetime],
        time_range_end: Optional[datetime],
        email_limit: Optional[int],
        messenger_limit: Optional[int],
        overall_limit: Optional[int],
        force_reload: bool
    ) -> List[Dict[str, Any]]:
        """메시지 수집"""
        logger.info("📥 메시지 수집 중...")
        
        # 시간 범위 설정
        time_range = None
        if time_range_start or time_range_end:
            time_range = {
                "start": time_range_start,
                "end": time_range_end
            }
        
        # DataSourceManager를 통해 메시지 수집
        collect_options = {
            "email_limit": email_limit,
            "messenger_limit": messenger_limit,
            "overall_limit": overall_limit,
            "time_range": time_range,
            "force_reload": force_reload,
        }
        
        messages = await self._data_source_manager.collect_messages(collect_options)
        
        # 메시지 병합 (연속된 메시지 합치기)
        from main import coalesce_messages, _sort_key
        merged = coalesce_messages(messages, window_seconds=90, max_chars=1200)
        merged.sort(key=_sort_key, reverse=True)
        
        # 메시지 타입 분석
        email_count = len([m for m in merged if m.get("type") == "email" or m.get("platform") == "email"])
        message_count = len([m for m in merged if m.get("type") == "messenger" or m.get("platform") == "messenger"])
        other_count = len(merged) - email_count - message_count
        
        logger.info(
            f"📦 메시지 수집 완료: 이메일 {email_count}개, 메신저 {message_count}개, "
            f"기타 {other_count}개 (총 {len(merged)}개)"
        )
        
        return merged
    
    async def _rank_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[tuple]:
        """우선순위 분류"""
        logger.info("🎯 우선순위 분류 중...")
        ranked = await self._priority_ranker.rank_messages(messages)
        logger.debug(f"우선순위 분류 완료: {len(ranked)}개")
        return ranked
    
    async def _summarize_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Any]:
        """메시지 요약"""
        logger.info(f"📝 상위 {len(messages)}개 메시지 상세 분석 중...")
        summaries = await self._summarizer.batch_summarize(messages)
        logger.debug(f"메시지 요약 완료: {len(summaries)}개")
        return summaries
    
    async def _extract_actions(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Any]:
        """액션 추출"""
        logger.info("⚡ 액션 추출 중...")
        user_email = self._user_profile.get("email_address", "pm.1@quickchat.dev")
        actions = await self._action_extractor.batch_extract_actions(
            messages,
            user_email=user_email
        )
        logger.debug(f"액션 추출 완료: {len(actions)}개")
        return actions
    
    def _merge_results(
        self,
        ranked_messages: List[tuple],
        summaries: List[Any],
        actions: List[Any]
    ) -> List[Dict[str, Any]]:
        """분석 결과 병합"""
        logger.debug("🔗 분석 결과 병합 중...")
        
        # 상위 메시지에 대한 요약 맵 생성
        top_messages = [m for (m, _) in ranked_messages][:len(summaries)]
        summary_by_id = {}
        for m, s in zip(top_messages, summaries):
            if s and not getattr(s, "original_id", None):
                s.original_id = m.get("msg_id")
            summary_by_id[m["msg_id"]] = s
        
        # 액션 맵 생성
        actions_by_id = {}
        for a in actions:
            src = getattr(a, "source_message_id", None) or (
                a.get("source_message_id") if isinstance(a, dict) else None
            )
            if not src:
                continue
            actions_by_id.setdefault(src, []).append(a)
        
        # 결과 병합 (전체 랭킹 순서 보존)
        results = []
        for message, priority in ranked_messages:
            mid = message["msg_id"]
            s = summary_by_id.get(mid)
            pr = priority.to_dict() if hasattr(priority, "to_dict") else priority
            acts = [
                x.to_dict() if hasattr(x, "to_dict") else x
                for x in actions_by_id.get(mid, [])
            ]
            results.append({
                "message": message,
                "summary": (
                    s.to_dict() if hasattr(s, "to_dict") else (s.__dict__ if s else None)
                ),
                "priority": pr,
                "actions": acts,
                "analysis_timestamp": datetime.now().isoformat()
            })
        
        logger.debug(f"결과 병합 완료: {len(results)}개")
        return results
    
    def _generate_todo_list(
        self,
        analysis_results: List[Dict[str, Any]],
        persona_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """TODO 리스트 생성 (중복 제거 및 requester 필드 포함)
        
        Args:
            analysis_results: 분석 결과 리스트
            persona_name: 페르소나 이름 (requester로 사용)
        """
        logger.info("📋 TODO 리스트 생성 중...")
        
        todo_items: List[Dict] = []
        priority_value = {"high": 3, "medium": 2, "low": 1}
        
        # 통계
        total_actions = 0
        created_count = 0
        prevented_count = 0
        
        def _parse_deadline(d: str | None) -> datetime:
            if not d:
                return datetime.max.replace(tzinfo=timezone.utc)
            try:
                return datetime.fromisoformat(d.replace("Z", "+00:00"))
            except Exception:
                return datetime.max.replace(tzinfo=timezone.utc)
        
        for result in analysis_results:
            actions = result.get("actions") or []
            priority_obj = result.get("priority") or {}
            priority_level = (
                priority_obj.get("priority_level")
                if isinstance(priority_obj, dict)
                else getattr(priority_obj, "priority_level", "low")
            ).lower()
            
            # 원본 메시지 정보
            message = result.get("message", {})
            source_message_id = message.get("msg_id") or message.get("id")
            recipient_type = (message.get("recipient_type") or "to").lower()
            source_type = "메일" if message.get("platform") == "email" else "메시지"
            
            for action in actions:
                if recipient_type != "to":
                    continue

                total_actions += 1
                
                # 액션에서 정보 추출
                if isinstance(action, dict):
                    title = action.get("title") or action.get("description") or "제목 없음"
                    description = action.get("description") or ""
                    deadline = action.get("deadline")
                    todo_type = action.get("type", "task")
                    action_source_id = action.get("source_message_id") or source_message_id
                    requester = action.get("requester") or message.get("sender") or "Unknown"
                else:
                    title = getattr(action, "title", None) or getattr(action, "description", "제목 없음")
                    description = getattr(action, "description", "")
                    deadline = getattr(action, "deadline", None)
                    todo_type = getattr(action, "type", "task")
                    action_source_id = getattr(action, "source_message_id", None) or source_message_id
                    requester = getattr(action, "requester", None) or message.get("sender") or "Unknown"
                
                # 중복 체크 (중복 제거 서비스가 있을 때만)
                if self._deduplication_service and action_source_id:
                    should_create, existing_id = self._deduplication_service.should_create_todo(
                        source_message=action_source_id,
                        todo_type=todo_type,
                        repository=self._todo_repository
                    )
                    
                    if not should_create:
                        logger.debug(
                            f"중복 TODO 생성 방지: source={action_source_id}, "
                            f"existing={existing_id}"
                        )
                        prevented_count += 1
                        continue
                
                # TODO 생성
                todo_id = f"todo_{datetime.now().timestamp()}_{created_count}"
                
                # source_message에 전체 메시지 내용 저장 (프로젝트 태그 추출용)
                import json
                source_message_full = json.dumps(message, ensure_ascii=False) if message else action_source_id
                
                todo_item = {
                    "id": todo_id,
                    "title": title,
                    "description": description,
                    "priority": priority_level,
                    "deadline": deadline,
                    "source_message": source_message_full,  # 전체 메시지 JSON
                    "type": todo_type,
                    "requester": requester,  # 실제 요청자 (보낸 사람)
                    "created_at": datetime.now().isoformat(),
                    "status": "pending",
                    "recipient_type": recipient_type,
                    "source_type": source_type,
                    "persona_name": persona_name,
                }
                
                todo_items.append(todo_item)
                created_count += 1
                
                # 중복 제거 서비스에 등록
                if self._deduplication_service and action_source_id:
                    self._deduplication_service.register_todo(action_source_id, todo_id)
        
        # 우선순위 및 마감일 기준 정렬
        todo_items.sort(
            key=lambda x: (
                -priority_value.get(x["priority"], 0),
                _parse_deadline(x.get("deadline"))
            )
        )
        
        # 통계 업데이트
        self._stats["todos_created"] = created_count
        self._stats["todos_prevented"] = prevented_count
        
        # 추출률 계산
        if total_actions > 0:
            extraction_rate = (created_count / total_actions) * 100
            self._stats["extraction_rate"] = extraction_rate
            
            logger.info(
                f"📋 TODO 리스트 생성 완료: {created_count}개 생성, "
                f"{prevented_count}개 중복 방지 (추출률: {extraction_rate:.1f}%)"
            )
            
            # 추출률이 너무 낮으면 경고
            if extraction_rate < 5.0:
                logger.warning(
                    f"⚠️ TODO 추출률이 낮습니다 ({extraction_rate:.1f}%). "
                    f"LLM 분석 품질을 확인하세요."
                )
        else:
            logger.info(f"📋 TODO 리스트 생성 완료: {created_count}개")
        
        return todo_items
    
    async def _summarize_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """전체 대화 요약"""
        try:
            logger.debug("💬 전체 대화 요약 중...")
            from main import _sort_key
            sorted_messages = sorted(messages, key=_sort_key)
            
            if not sorted_messages:
                return None
            
            conv = await self._summarizer.summarize_conversation(sorted_messages)
            
            if isinstance(conv, dict):
                return conv
            elif hasattr(conv, "summary"):
                maybe_dict = getattr(conv, "__dict__", None)
                if isinstance(maybe_dict, dict):
                    return maybe_dict
                return {"summary": getattr(conv, "summary", "")}
            elif isinstance(conv, str):
                return {"summary": conv}
            
            return None
        except Exception as e:
            logger.warning(f"대화 요약 실패: {e}")
            return None
    
    async def _build_analysis_report(
        self,
        analysis_results: List[Dict[str, Any]],
        conversation_summary: Optional[Dict[str, Any]]
    ) -> str:
        """분석 리포트 텍스트 생성"""
        logger.debug("📊 분석 리포트 생성 중...")
        
        from main import build_overall_analysis_text
        
        # 기존 함수 재사용 (self 파라미터를 위해 임시 객체 생성)
        class TempAssistant:
            def __init__(self, summarizer):
                self.summarizer = summarizer
        
        temp = TempAssistant(self._summarizer)
        report_text = await build_overall_analysis_text(temp, analysis_results)
        
        return report_text
    
    def _calculate_summary(
        self,
        messages: List[Dict[str, Any]],
        todo_list: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """통계 계산"""
        email_count = sum(
            1 for m in messages
            if m.get("type") == "email" or m.get("platform") == "email"
        )
        chat_count = sum(
            1 for m in messages
            if m.get("type") == "messenger" or m.get("platform") == "messenger"
        )
        
        # 우선순위별 카운트
        high_count = sum(
            1 for r in analysis_results
            if (r.get("priority") or {}).get("priority_level", "").lower() == "high"
        )
        medium_count = sum(
            1 for r in analysis_results
            if (r.get("priority") or {}).get("priority_level", "").lower() == "medium"
        )
        low_count = sum(
            1 for r in analysis_results
            if (r.get("priority") or {}).get("priority_level", "").lower() == "low"
        )
        
        return {
            "total_messages": len(messages),
            "email_count": email_count,
            "chat_count": chat_count,
            "todo_count": len(todo_list),
            "high_priority_count": high_count,
            "medium_priority_count": medium_count,
            "low_priority_count": low_count
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """빈 결과 반환"""
        return {
            "todo_list": [],
            "messages": [],
            "analysis_results": [],
            "summary": {
                "total_messages": 0,
                "email_count": 0,
                "chat_count": 0,
                "todo_count": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "low_priority_count": 0
            },
            "conversation_summary": None,
            "analysis_report_text": ""
        }
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """파이프라인 통계 반환"""
        stats = self._stats.copy()
        
        # 중복 제거 서비스 통계 추가
        if self._deduplication_service:
            dedup_stats = self._deduplication_service.get_deduplication_stats()
            stats["deduplication"] = dedup_stats
        
        return stats
    
    def cleanup_duplicate_todos(self) -> Dict[str, int]:
        """기존 중복 TODO 정리
        
        Returns:
            {"removed": int, "kept": int}
        """
        if not self._deduplication_service or not self._todo_repository:
            logger.warning("중복 제거 서비스 또는 Repository가 없어 정리를 건너뜁니다.")
            return {"removed": 0, "kept": 0}
        
        logger.info("🗑️ 기존 중복 TODO 정리 시작...")
        result = self._deduplication_service.cleanup_duplicates(self._todo_repository)
        logger.info(f"✅ 중복 TODO 정리 완료: 제거={result['removed']}개, 유지={result['kept']}개")
        
        return result
