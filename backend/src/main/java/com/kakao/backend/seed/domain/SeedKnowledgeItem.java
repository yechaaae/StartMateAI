package com.kakao.backend.seed.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "seed_knowledge_items")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SeedKnowledgeItem extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "agent_type", nullable = false)
    private String agentType;

    @Column(name = "category", nullable = false)
    private String category;

    @Column(name = "title", nullable = false)
    private String title;

    @Lob
    @Column(name = "content", nullable = false, columnDefinition = "text")
    private String content;

    @Lob
    @Column(name = "tags", columnDefinition = "text")
    private String tags;

    @Column(name = "source_type")
    private String sourceType;

    @Column(name = "source_url")
    private String sourceUrl;

    public static SeedKnowledgeItem create(String agentType, String category, String title, String content, String tags) {
        SeedKnowledgeItem item = new SeedKnowledgeItem();
        item.setAgentType(agentType);
        item.setCategory(category);
        item.setTitle(title);
        item.setContent(content);
        item.setTags(tags);
        item.setSourceType("demo_seed");
        return item;
    }
}
