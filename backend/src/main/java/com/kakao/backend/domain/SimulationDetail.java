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
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "simulation_detail")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SimulationDetail {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "simulation_result_id", nullable = false)
    private SimulationResult simulationResult;

    @Column(name = "day")
    private Integer day;

    @Column(name = "title")
    private String title;

    @Lob
    @Column(name = "action_item", columnDefinition = "text")
    private String actionItem;

    @Lob
    @Column(name = "risk_message", columnDefinition = "text")
    private String riskMessage;

    @Lob
    @Column(name = "recommendation", columnDefinition = "text")
    private String recommendation;
}
