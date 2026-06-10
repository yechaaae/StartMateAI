from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.rag.legal_retriever import LegalRetriever, LegalSearchResult
from app.schemas import AgentResponse, LegalRequest, Source


class LegalAgent(BaseAgent):
    name = "LegalAgent"

    def __init__(self, llm, retriever: LegalRetriever):
        super().__init__(llm)
        self.retriever = retriever

    async def run(self, request: LegalRequest) -> AgentResponse:
        domains = request.domains or self._infer_domains(request.query)
        expanded_query = self._expanded_query(request.query, domains)
        results = self._search_results(expanded_query, domains, request.limit)

        issues = self._issues_from_results(results, request.query)
        citations = [self._citation(result) for result in results]
        missing_inputs = self._missing_inputs(request.query)
        risks = [
            "법령 RAG 결과는 법률 자문이 아니라 체크리스트입니다. 실제 신고/허가 여부는 관할 지자체나 전문가에게 확인해야 합니다."
        ]
        if not results:
            risks.append("관련 조문을 찾지 못했습니다. 업종, 판매 방식, 장소, 고용 여부를 더 구체화해야 합니다.")

        position = self._position(issues, results, citations)
        recommendation = self._recommendation(issues, missing_inputs, citations)
        score = self._score(results)
        data = self.agent_data(
            position=position,
            evidence={
                "query": request.query,
                "expanded_query": expanded_query,
                "domains": domains,
                "top_citations": citations[:5],
            },
            score=score,
            risks=risks,
            assumptions=[
                "수집 법령은 국가법령정보센터 Open API 기준입니다.",
                "조문 검색은 text-embedding-3-large 임베딩과 키워드 보정을 함께 사용합니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation=recommendation,
            payload={
                "legal_issues": issues,
                "citations": citations,
                "search_results": [self._result_payload(result) for result in results],
                "coverage": {
                    "retrieved_count": len(results),
                    "domains": domains,
                    "vector_store_count": self._safe_count(),
                },
                "disclaimer": "일반 정보 제공이며 법률 자문이 아닙니다.",
            },
        )
        summary = self._summary_fallback(issues, citations)
        return AgentResponse(
            intent="legal",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "업종, 판매 장소, 제조 장소, 온라인 판매 여부를 확정",
                "관할 지자체 위생/인허가 부서에 영업신고 대상 여부 확인",
                "포장 판매나 온라인 주문이 있으면 표시광고/전자상거래/개인정보 체크",
            ],
            sources=[
                Source(
                    title=f"{item['law_name']} {item['article_no']} {item['article_title']}".strip(),
                    url=item.get("url"),
                    note=item.get("excerpt"),
                )
                for item in citations[:5]
            ],
            warnings=risks,
        )

    def _search_results(self, query: str, domains: list[str], limit: int) -> list[LegalSearchResult]:
        if not domains:
            return self.retriever.search(query, top_k=limit)

        merged: dict[str, LegalSearchResult] = {}
        per_domain_limit = max(2, min(4, limit))
        for domain in domains:
            domain_query = self._domain_query(query, domain)
            for result in self.retriever.search(domain_query, top_k=per_domain_limit, domains=[domain]):
                existing = merged.get(result.id)
                if existing is None or result.score > existing.score:
                    merged[result.id] = result

        if len(merged) < limit:
            for result in self.retriever.search(query, top_k=limit * 2):
                existing = merged.get(result.id)
                if existing is None or result.score > existing.score:
                    merged[result.id] = result

        results = list(merged.values())
        results.sort(key=lambda item: (self._domain_priority(item.metadata), item.score), reverse=True)
        return results[:limit]

    def _domain_query(self, query: str, domain: str) -> str:
        additions = {
            "food": "식품위생법 영업신고 시설기준 영업허가",
            "popup": "팝업 플리마켓 오프라인 판매 영업신고",
            "permit": "영업신고 허가 등록 신고 대상",
            "facility": "시설기준 업종별 시설기준 영업 시설",
            "labeling": "식품 표시 광고 원재료 표시",
            "advertising": "표시 광고 부당 광고",
            "online": "전자상거래 통신판매 고지 청약철회 소비자보호",
            "privacy": "개인정보 수집 이용 동의 처리",
            "tax": "부가가치세 사업자등록 간이과세",
            "lease": "상가 임대차 계약 보증금",
            "labor": "근로계약 최저임금 아르바이트",
            "intellectual_property": "상표 저작권 브랜드 로고 콘텐츠",
        }
        return f"{query} {additions.get(domain, domain)}"

    def _domain_priority(self, metadata: dict[str, Any]) -> float:
        domains = str(metadata.get("domains", ""))
        priority = 0.0
        if "online" in domains:
            priority += 0.07
        if "food" in domains:
            priority += 0.06
        if "permit" in domains:
            priority += 0.05
        if "labeling" in domains or "advertising" in domains:
            priority += 0.04
        return priority

    def _infer_domains(self, query: str) -> list[str]:
        text = query.lower()
        domains: list[str] = []
        checks = [
            ("food", ["쿠키", "식품", "음식", "카페", "디저트", "팝업", "위생", "제조", "판매"]),
            ("popup", ["팝업", "플리마켓", "부스", "행사", "오프라인"]),
            ("permit", ["신고", "허가", "인허가", "등록", "영업신고"]),
            ("facility", ["시설", "주방", "제조장", "시설기준"]),
            ("labeling", ["표시", "라벨", "원재료", "영양", "알레르기"]),
            ("advertising", ["광고", "홍보", "후기", "과장"]),
            ("online", ["온라인", "sns", "인스타", "배송", "주문", "통신판매"]),
            ("privacy", ["개인정보", "전화번호", "예약자", "주소", "동의"]),
            ("tax", ["세금", "세무", "부가세", "사업자등록"]),
            ("lease", ["임대", "계약", "보증금", "상가"]),
            ("labor", ["고용", "알바", "아르바이트", "직원", "최저임금"]),
            ("intellectual_property", ["상표", "저작권", "브랜드", "로고", "음악", "사진"]),
        ]
        for domain, keywords in checks:
            if any(keyword in text for keyword in keywords):
                domains.append(domain)
        return self._unique(domains)

    def _expanded_query(self, query: str, domains: list[str]) -> str:
        additions = []
        if "food" in domains:
            additions.extend(["식품위생법", "영업신고", "시설기준", "위생"])
        if "labeling" in domains or "advertising" in domains:
            additions.extend(["표시광고", "식품 등의 표시 광고"])
        if "online" in domains:
            additions.extend(["통신판매", "전자상거래", "청약철회"])
        if "privacy" in domains:
            additions.extend(["개인정보 수집 이용 동의"])
        if "labor" in domains:
            additions.extend(["근로계약", "최저임금"])
        if "intellectual_property" in domains:
            additions.extend(["상표", "저작권"])
        return " ".join([query, *self._unique(additions)])

    def _issues_from_results(self, results: list[LegalSearchResult], query: str) -> list[dict[str, Any]]:
        issues = []
        for result in results[:5]:
            title = str(result.metadata.get("article_title") or "")
            law_name = str(result.metadata.get("law_name") or "")
            issue = self._issue_label(law_name, title, result.text, query)
            issues.append(
                {
                    "issue": issue,
                    "status": "확인 필요",
                    "basis": f"{law_name} 제{result.metadata.get('article_no')}조 {title}".strip(),
                    "why_relevant": self._why_relevant(result),
                    "score": result.score,
                }
            )
        return issues

    def _issue_label(self, law_name: str, title: str, text: str, query: str) -> str:
        haystack = " ".join([law_name, title, text, query])
        if "영업신고" in haystack or "영업의 신고" in haystack:
            return "영업신고 대상 여부"
        if "시설기준" in haystack:
            return "업종별 시설기준 충족 여부"
        if "표시" in haystack or "광고" in haystack:
            return "표시ㆍ광고 준수 여부"
        if "통신판매" in haystack or "전자상거래" in haystack:
            return "통신판매/온라인 판매 고지 의무"
        if "개인정보" in haystack:
            return "개인정보 수집ㆍ이용 동의"
        if "상표" in haystack:
            return "상표권 충돌 가능성"
        if "저작권" in haystack:
            return "콘텐츠 저작권 사용 리스크"
        if "근로" in haystack or "최저임금" in haystack:
            return "고용/근로계약 리스크"
        return title or law_name or "관련 법령 확인"

    def _citation(self, result: LegalSearchResult) -> dict[str, Any]:
        return {
            "law_name": result.metadata.get("law_name"),
            "article_no": result.metadata.get("article_no"),
            "article_title": result.metadata.get("article_title"),
            "url": result.metadata.get("url"),
            "score": result.score,
            "excerpt": result.text[:240],
        }

    def _result_payload(self, result: LegalSearchResult) -> dict[str, Any]:
        return {
            "id": result.id,
            "text": result.text,
            "metadata": result.metadata,
            "distance": result.distance,
            "score": result.score,
        }

    def _missing_inputs(self, query: str) -> list[str]:
        missing = []
        if not any(word in query for word in ["온라인", "오프라인", "팝업", "매장", "배송"]):
            missing.append("판매 방식")
        if not any(word in query for word in ["제조", "주방", "납품", "직접", "구매"]):
            missing.append("제조/조리 장소")
        if not any(word in query for word in ["구미", "서울", "부산", "대구", "경북", "지역"]):
            missing.append("영업 지역")
        return missing

    def _position(
        self,
        issues: list[dict[str, Any]],
        results: list[LegalSearchResult],
        citations: list[dict[str, Any]],
    ) -> str:
        if not results:
            return "질문만으로는 관련 법령을 충분히 특정하기 어렵습니다."
        labels = self._unique([issue["issue"] for issue in issues[:3]])
        refs = self._citation_labels(citations[:3])
        return f"우선 확인할 법률 이슈는 {', '.join(labels)}입니다. 참조 조문: {', '.join(refs)}."

    def _recommendation(
        self,
        issues: list[dict[str, Any]],
        missing_inputs: list[str],
        citations: list[dict[str, Any]],
    ) -> str:
        refs = self._citation_labels(citations[:3])
        reference_text = f" 참조: {', '.join(refs)}." if refs else ""
        if missing_inputs:
            return f"{', '.join(missing_inputs)}을 먼저 확정한 뒤 관할기관에 신고/허가 여부를 확인하세요.{reference_text}"
        if issues:
            issue_text = "; ".join(f"{item['issue']}은 {item['basis']} 기준으로 확인" for item in issues[:3])
            return f"{issue_text}. 실제 적용 여부는 관할기관에 확인하세요.{reference_text}"
        return "업종과 판매 방식을 구체화해 다시 법령 검색을 진행하세요."

    def _summary_fallback(self, issues: list[dict[str, Any]], citations: list[dict[str, Any]]) -> str:
        if not citations:
            return "관련 법령 근거를 충분히 찾지 못했습니다. 판매 방식과 업종을 더 구체화해 주세요."
        issue_lines = [
            f"{index + 1}. {item['issue']}: {item['basis']} 기준으로 확인 필요"
            for index, item in enumerate(issues[:5])
        ]
        citation_lines = [
            f"- {label}: {citation.get('excerpt', '')[:120]}"
            for label, citation in zip(self._citation_labels(citations[:5]), citations[:5], strict=False)
        ]
        return (
            "확인해야 할 항목:\n"
            + "\n".join(issue_lines)
            + "\n\n참조 법령:\n"
            + "\n".join(citation_lines)
            + "\n\n위 조문은 일반 체크리스트 근거이며, 실제 신고/허가 대상 여부는 관할 지자체에 확인해야 합니다."
        )

    def _citation_labels(self, citations: list[dict[str, Any]]) -> list[str]:
        labels = []
        for item in citations:
            law_name = item.get("law_name")
            article_no = item.get("article_no")
            title = item.get("article_title")
            if not law_name:
                continue
            article = f" 제{article_no}조" if article_no else ""
            title_text = f"({title})" if title else ""
            labels.append(f"{law_name}{article}{title_text}")
        return labels

    def _why_relevant(self, result: LegalSearchResult) -> str:
        law = result.metadata.get("law_name", "관련 법령")
        title = result.metadata.get("article_title", "관련 조문")
        return f"{law}의 {title} 조문이 질문의 법적 체크포인트와 유사하게 검색되었습니다."

    def _score(self, results: list[LegalSearchResult]) -> int:
        if not results:
            return 0
        return max(0, min(100, int(results[0].score * 100)))

    def _safe_count(self) -> int | None:
        try:
            return self.retriever.count()
        except Exception:
            return None

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            item = str(value).strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result
