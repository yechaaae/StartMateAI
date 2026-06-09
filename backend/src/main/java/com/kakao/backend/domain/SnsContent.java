package com.kakao.backend.domain;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "sns_content")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SnsContent extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "business_idea_option_id")
    private BusinessIdeaOption businessIdeaOption;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "operation_feedback_id")
    private OperationFeedback operationFeedback;

    @Column(name = "chat_room_id")
    private Long chatRoomId;

    @Column(name = "campaign_title")
    private String campaignTitle;

    @Column(name = "target_customer")
    private String targetCustomer;

    @Column(name = "brand_tone")
    private String brandTone;

    @Column(name = "event_date")
    private LocalDate eventDate;

    @OneToMany(mappedBy = "snsContent", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SnsContentItem> items = new ArrayList<>();
}
