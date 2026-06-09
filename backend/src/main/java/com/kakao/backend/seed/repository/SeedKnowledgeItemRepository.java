package com.kakao.backend.seed.repository;

import com.kakao.backend.seed.domain.SeedKnowledgeItem;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SeedKnowledgeItemRepository extends JpaRepository<SeedKnowledgeItem, Long> {

    Optional<SeedKnowledgeItem> findByAgentTypeAndCategoryAndTitle(String agentType, String category, String title);
}
