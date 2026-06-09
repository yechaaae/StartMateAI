package com.kakao.backend.domain;

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
@Table(name = "business_idea_result")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BusinessIdeaResult extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @Column(name = "chat_room_id")
    private Long chatRoomId;

    @Column(name = "title", nullable = false)
    private String title;

    @Lob
    @Column(name = "summary", columnDefinition = "text")
    private String summary;

    @Lob
    @Column(name = "input_snapshot", columnDefinition = "text")
    private String inputSnapshot;

    @OneToMany(mappedBy = "ideaResult", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<BusinessIdeaOption> options = new ArrayList<>();
}
