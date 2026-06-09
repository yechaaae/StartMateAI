package com.kakao.backend.seed.service;

import com.kakao.backend.seed.domain.SeedKnowledgeItem;
import com.kakao.backend.seed.repository.SeedKnowledgeItemRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SeedKnowledgeService {

    private final SeedKnowledgeItemRepository repository;

    public SeedKnowledgeService(SeedKnowledgeItemRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public int importDefaultItems() {
        List<SeedKnowledgeItem> items = List.of(
                SeedKnowledgeItem.create("profile", "business_stage", "창업단계 분류", "idea, preparing, mvp, pre_revenue, revenue, scaling", "profile,business_stage"),
                SeedKnowledgeItem.create("profile", "founder_type", "창업자 유형", "pre_founder, individual_business, corporation, re_founder", "profile,founder_type"),
                SeedKnowledgeItem.create("support_program", "support_type", "지원유형 분류", "grant, loan, guarantee, education, mentoring, space, rnd, marketing", "support,type"),
                SeedKnowledgeItem.create("legal", "checklist", "법률 응답 원칙", "법률 자문처럼 단정하지 않고 체크리스트, 확인 필요, 전문가 상담 권장 형태로 응답한다.", "legal,checklist"),
                SeedKnowledgeItem.create("operation", "checklist", "오픈 준비 체크리스트", "인허가 확인, 사업자등록, 위생/안전 점검, POS/정산, CS 응대 문구 준비", "operation,checklist"),
                SeedKnowledgeItem.create("marketing", "playbook", "초기 마케팅 플레이북", "지역 키워드, 짧은 릴스 훅, 예약/문의 CTA, 후기 수집 루프를 먼저 만든다.", "marketing,playbook"),
                SeedKnowledgeItem.create("finance_admin", "template", "초기 비용 템플릿", "보증금, 임대료, 장비, 초도재고, 마케팅비, 기타 고정비를 분리해 계산한다.", "finance,template")
        );
        int count = 0;
        for (SeedKnowledgeItem item : items) {
            repository.findByAgentTypeAndCategoryAndTitle(item.getAgentType(), item.getCategory(), item.getTitle())
                    .ifPresentOrElse(existing -> {
                        existing.setContent(item.getContent());
                        existing.setTags(item.getTags());
                        repository.save(existing);
                    }, () -> repository.save(item));
            count++;
        }
        return count;
    }
}
