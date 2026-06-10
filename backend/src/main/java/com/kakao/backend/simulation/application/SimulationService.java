package com.kakao.backend.simulation.application;

import com.kakao.backend.idea.domain.BusinessIdeaOption;
import com.kakao.backend.simulation.domain.SimulationAssumption;
import com.kakao.backend.simulation.domain.SimulationDailyMetric;
import com.kakao.backend.simulation.domain.SimulationLocation;
import com.kakao.backend.simulation.domain.SimulationResult;
import com.kakao.backend.simulation.dto.SimulationSaveRequest;
import com.kakao.backend.simulation.infrastructure.SimulationLocationRepository;
import com.kakao.backend.simulation.infrastructure.SimulationResultRepository;
import com.kakao.backend.workspace.domain.Workspace;
import jakarta.persistence.EntityManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class SimulationService {

    private final SimulationResultRepository resultRepository;
    private final SimulationLocationRepository locationRepository;
    private final EntityManager em;

    public SimulationService(SimulationResultRepository resultRepository,
                             SimulationLocationRepository locationRepository,
                             EntityManager em) {
        this.resultRepository = resultRepository;
        this.locationRepository = locationRepository;
        this.em = em;
    }

    public Long saveSimulation(SimulationSaveRequest request) {
        Workspace workspace = em.getReference(Workspace.class, request.workspaceId());
        
        BusinessIdeaOption ideaOption = null;
        if (request.businessIdeaOptionId() != null) {
            ideaOption = em.getReference(BusinessIdeaOption.class, request.businessIdeaOptionId());
        }

        // 1. Location 저장
        SimulationLocation location = SimulationLocation.create();
        location.setWorkspace(workspace);
        if (request.location() != null) {
            location.setAddress(request.location().address());
            location.setRoadAddress(request.location().roadAddress());
            location.setLatitude(request.location().latitude());
            location.setLongitude(request.location().longitude());
            location.setKakaoPlaceId(request.location().kakaoPlaceId());
            location.setRoadviewPanoId(request.location().roadviewPanoId());
            location.setMonthlyRent(request.location().monthlyRent());
        }
        locationRepository.save(location);

        // 2. Result 생성
        SimulationResult result = SimulationResult.create();
        result.setWorkspace(workspace);
        result.setBusinessIdeaOption(ideaOption);
        result.setSimulationLocation(location);
        result.setSimulationType("MOCK_30_DAYS");
        result.setInitialBudget(request.assumption() != null ? request.assumption().initialBudget() : null);
        
        if (request.summary() != null) {
            result.setExpectedRevenue(request.summary().totalRevenue());
            result.setExpectedCost(request.summary().totalCost());
            result.setExpectedProfit(request.summary().totalProfit());
            result.setBreakEvenPoint(request.summary().bepDay());
        }

        // 3. Assumption 설정
        if (request.assumption() != null) {
            SimulationAssumption assumption = SimulationAssumption.create();
            assumption.setSimulationResult(result);
            assumption.setInitialBudget(request.assumption().initialBudget());
            assumption.setPricePerOrder(request.assumption().pricePerOrder());
            assumption.setExpectedDailyOrders(request.assumption().expectedDailyOrders());
            assumption.setOperatingDays(request.assumption().operatingDays());
            assumption.setVariableCostRate(request.assumption().variableCostRate());
            assumption.setMonthlyRent(request.assumption().monthlyRent());
            assumption.setLaborCost(request.assumption().laborCost());
            assumption.setMarketingCost(request.assumption().marketingCost());
            assumption.setOtherFixedCost(request.assumption().otherFixedCost());
            result.setAssumption(assumption);
        }

        // 4. Daily Metrics 설정
        if (request.dailyMetrics() != null) {
            for (SimulationSaveRequest.DailyMetricDto dto : request.dailyMetrics()) {
                SimulationDailyMetric metric = SimulationDailyMetric.create();
                metric.setSimulationResult(result);
                metric.setDay(dto.day());
                metric.setOrders(dto.orders());
                metric.setRevenue(dto.revenue());
                metric.setVariableCost(dto.variableCost());
                metric.setFixedCost(dto.fixedCost());
                metric.setProfit(dto.profit());
                metric.setCumulativeProfit(dto.cumulativeProfit());
                result.getDailyMetrics().add(metric);
            }
        }

        SimulationResult saved = resultRepository.save(result);
        return saved.getId();
    }
}
