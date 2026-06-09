package com.kakao.backend.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "sns_content_item")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SnsContentItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "sns_content_id", nullable = false)
    private SnsContent snsContent;

    @Column(name = "content_type")
    private String contentType;

    @Column(name = "title")
    private String title;

    @Lob
    @Column(name = "content", columnDefinition = "text")
    private String content;

    @Lob
    @Column(name = "hashtags", columnDefinition = "text")
    private String hashtags;

    @Column(name = "scheduled_at")
    private LocalDateTime scheduledAt;
}
