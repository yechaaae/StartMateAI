package com.kakao.backend.idea.infrastructure;

import com.kakao.backend.idea.domain.BusinessIdeaResult;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BusinessIdeaResultRepository extends JpaRepository<BusinessIdeaResult, Long> {
}
