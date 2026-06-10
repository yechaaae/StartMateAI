package com.kakao.backend.operation.infrastructure;

import com.kakao.backend.operation.domain.OperationFeedback;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OperationFeedbackRepository extends JpaRepository<OperationFeedback, Long> {
}
