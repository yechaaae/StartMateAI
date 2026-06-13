package com.kakao.backend.workspace.domain;

import com.kakao.backend.chat.domain.ChatRoom;
import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.idea.domain.BusinessIdeaOption;
import com.kakao.backend.idea.domain.BusinessIdeaResult;
import com.kakao.backend.marketing.domain.SnsContent;
import com.kakao.backend.operation.domain.OperationFeedback;
import com.kakao.backend.plan.domain.BusinessPlan;
import com.kakao.backend.policy.domain.SupportProgramMatch;
import com.kakao.backend.simulation.domain.SimulationResult;
import com.kakao.backend.user.model.User;
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
@Table(name = "workspace")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Workspace extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "status", nullable = false)
    private String status;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "selected_idea_id")
    private BusinessIdeaOption selectedIdea;

    // 사용자가 확정한 추천 아이템 스냅샷 (BusinessIdeaOption 영속 여부와 무관하게 표시용으로 저장)
    @Column(name = "selected_idea_title")
    private String selectedIdeaTitle;

    @Column(name = "selected_idea_category")
    private String selectedIdeaCategory;

    @Column(name = "selected_idea_score")
    private Integer selectedIdeaScore;

    @Column(name = "selected_idea_reason", columnDefinition = "text")
    private String selectedIdeaReason;

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<BusinessIdeaResult> businessIdeaResults = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SimulationResult> simulationResults = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SupportProgramMatch> supportProgramMatches = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<BusinessPlan> businessPlans = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OperationFeedback> operationFeedbacks = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SnsContent> snsContents = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<SavedResult> savedResults = new ArrayList<>();

    @OneToMany(mappedBy = "workspace", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<ChatRoom> chatRooms = new ArrayList<>();

    public static Workspace create(String title, String status) {
        Workspace workspace = new Workspace();
        workspace.setTitle(title);
        workspace.setStatus(status);
        return workspace;
    }

    // 확정한 아이템으로 워크스페이스 이름과 스냅샷을 갱신한다.
    public void applySelectedIdea(String ideaTitle, String category, Integer score, String reason) {
        if (ideaTitle != null && !ideaTitle.isBlank()) {
            this.title = ideaTitle.trim();
            this.selectedIdeaTitle = ideaTitle.trim();
        }
        this.selectedIdeaCategory = category;
        this.selectedIdeaScore = score;
        this.selectedIdeaReason = reason;
    }
}
