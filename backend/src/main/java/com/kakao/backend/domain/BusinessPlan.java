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
import java.util.ArrayList;
import java.util.List;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "business_plan")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BusinessPlan extends BaseTimeEntity {

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
    @JoinColumn(name = "support_program_recommendation_id")
    private SupportProgramRecommendation supportProgramRecommendation;

    @Column(name = "chat_room_id")
    private Long chatRoomId;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "status", nullable = false)
    private String status;

    @OneToMany(mappedBy = "businessPlan", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<BusinessPlanSection> sections = new ArrayList<>();
}
