package com.kakao.backend.simulation.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "simulation_assumption")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SimulationAssumption {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "simulation_result_id", nullable = false)
    private SimulationResult simulationResult;

    @Column(name = "initial_budget")
    private Integer initialBudget;

    @Column(name = "price_per_order")
    private Integer pricePerOrder;

    @Column(name = "expected_daily_orders")
    private Integer expectedDailyOrders;

    @Column(name = "operating_days")
    private Integer operatingDays;

    @Column(name = "variable_cost_rate")
    private Double variableCostRate;

    @Column(name = "monthly_rent")
    private Integer monthlyRent;

    @Column(name = "labor_cost")
    private Integer laborCost;

    @Column(name = "marketing_cost")
    private Integer marketingCost;

    @Column(name = "utility_cost")
    private Integer utilityCost;

    @Column(name = "other_fixed_cost")
    private Integer otherFixedCost;

    @Column(name = "scenario_name")
    private String scenarioName;

    public static SimulationAssumption create() {
        return new SimulationAssumption();
    }
}
