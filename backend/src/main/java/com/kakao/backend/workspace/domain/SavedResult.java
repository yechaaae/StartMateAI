package com.kakao.backend.workspace.domain;

import com.kakao.backend.common.domain.BaseCreatedEntity;
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
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "saved_result")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SavedResult extends BaseCreatedEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @Column(name = "result_type", nullable = false)
    private String resultType;

    @Column(name = "reference_id", nullable = false)
    private Long referenceId;

    @Column(name = "title", nullable = false)
    private String title;

    @Lob
    @Column(name = "summary", columnDefinition = "text")
    private String summary;
}
