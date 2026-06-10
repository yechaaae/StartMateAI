package com.kakao.backend.simulation.dto;

import java.util.List;

public record SimulationSaveRequest(
    Long workspaceId,
    Long businessIdeaOptionId,
    LocationDto location,
    AssumptionDto assumption,
    List<DailyMetricDto> dailyMetrics,
    SummaryDto summary
) {
    public record LocationDto(
        String address,
        String roadAddress,
        Double latitude,
        Double longitude,
        String kakaoPlaceId,
        Long roadviewPanoId,
        Integer monthlyRent
    ) {}

    public record AssumptionDto(
        Integer initialBudget,
        Integer pricePerOrder,
        Integer expectedDailyOrders,
        Integer operatingDays,
        Double variableCostRate,
        Integer monthlyRent,
        Integer laborCost,
        Integer marketingCost,
        Integer otherFixedCost
    ) {}

    public record DailyMetricDto(
        Integer day,
        Integer orders,
        Integer revenue,
        Integer variableCost,
        Integer fixedCost,
        Integer profit,
        Integer cumulativeProfit
    ) {}

    public record SummaryDto(
        Integer totalRevenue,
        Integer totalCost,
        Integer totalProfit,
        Integer bepDay
    ) {}
}
