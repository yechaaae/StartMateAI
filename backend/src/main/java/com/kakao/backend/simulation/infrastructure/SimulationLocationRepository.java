package com.kakao.backend.simulation.infrastructure;

import com.kakao.backend.simulation.domain.SimulationLocation;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SimulationLocationRepository extends JpaRepository<SimulationLocation, Long> {
}
