package com.kakao.backend.operation.domain;

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
import java.math.BigDecimal;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "operation_metric")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OperationMetric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "operation_feedback_id", nullable = false)
    private OperationFeedback operationFeedback;

    @Column(name = "metric_type")
    private String metricType;

    @Column(name = "metric_name")
    private String metricName;

    @Column(name = "metric_value", precision = 15, scale = 4)
    private BigDecimal metricValue;

    @Column(name = "unit")
    private String unit;

    @Lob
    @Column(name = "description", columnDefinition = "text")
    private String description;

    public static OperationMetric create(
            OperationFeedback operationFeedback,
            String metricType,
            String metricName,
            BigDecimal metricValue,
            String unit,
            String description
    ) {
        OperationMetric metric = new OperationMetric();
        metric.setOperationFeedback(operationFeedback);
        metric.setMetricType(metricType);
        metric.setMetricName(metricName);
        metric.setMetricValue(metricValue);
        metric.setUnit(unit);
        metric.setDescription(description);
        return metric;
    }
}
