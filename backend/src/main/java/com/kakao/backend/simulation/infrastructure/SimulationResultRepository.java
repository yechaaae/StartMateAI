package com.kakao.backend.simulation.infrastructure;

import com.kakao.backend.simulation.domain.SimulationResult;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SimulationResultRepository extends JpaRepository<SimulationResult, Long> {
}
