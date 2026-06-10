package com.kakao.backend.simulation.presentation;

import com.kakao.backend.simulation.application.SimulationService;
import com.kakao.backend.simulation.dto.SimulationSaveRequest;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/simulations")
public class SimulationController {

    private final SimulationService simulationService;

    public SimulationController(SimulationService simulationService) {
        this.simulationService = simulationService;
    }

    @PostMapping
    public ResponseEntity<Map<String, Long>> saveSimulation(@RequestBody SimulationSaveRequest request) {
        Long resultId = simulationService.saveSimulation(request);
        return ResponseEntity.ok(Map.of("id", resultId));
    }
}
