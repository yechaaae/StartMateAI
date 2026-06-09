package com.kakao.backend.policy.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.idea.domain.BusinessIdeaOption;
import com.kakao.backend.workspace.domain.Workspace;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
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
@Table(name = "support_program_match")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SupportProgramMatch extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "business_idea_option_id")
    private BusinessIdeaOption businessIdeaOption;

    @Column(name = "chat_room_id")
    private Long chatRoomId;

    @Lob
    @Column(name = "search_condition_snapshot", columnDefinition = "text")
    private String searchConditionSnapshot;

    @OneToMany(mappedBy = "supportProgramMatch", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SupportProgramRecommendation> recommendations = new ArrayList<>();
}
