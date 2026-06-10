package com.kakao.backend.simulation.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "simulation_daily_metric")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SimulationDailyMetric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "simulation_result_id", nullable = false)
    private SimulationResult simulationResult;

    @Column(name = "simulation_day")
    private Integer day;

    @Column(name = "orders")
    private Integer orders;

    @Column(name = "revenue")
    private Integer revenue;

    @Column(name = "variable_cost")
    private Integer variableCost;

    @Column(name = "fixed_cost")
    private Integer fixedCost;

    @Column(name = "profit")
    private Integer profit;

    @Column(name = "cumulative_profit")
    private Integer cumulativeProfit;

    @Column(name = "cash_balance")
    private Integer cashBalance;

    public static SimulationDailyMetric create() {
        return new SimulationDailyMetric();
    }
}
