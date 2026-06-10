package com.kakao.backend.simulation.domain;

import com.kakao.backend.common.domain.BaseTimeEntity;
import com.kakao.backend.workspace.domain.Workspace;
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
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Entity
@Table(name = "simulation_location")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SimulationLocation extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workspace_id", nullable = false)
    private Workspace workspace;

    @Column(name = "address")
    private String address;

    @Column(name = "road_address")
    private String roadAddress;

    @Column(name = "latitude")
    private Double latitude;

    @Column(name = "longitude")
    private Double longitude;

    @Column(name = "kakao_place_id")
    private String kakaoPlaceId;

    @Column(name = "roadview_pano_id")
    private Long roadviewPanoId;

    @Column(name = "building_name")
    private String buildingName;

    @Column(name = "floor")
    private String floor;

    @Column(name = "area_m2")
    private Double areaM2;

    @Column(name = "deposit")
    private Integer deposit;

    @Column(name = "monthly_rent")
    private Integer monthlyRent;

    @Column(name = "maintenance_fee")
    private Integer maintenanceFee;

    @Lob
    @Column(name = "selected_note", columnDefinition = "text")
    private String selectedNote;

    public static SimulationLocation create() {
        return new SimulationLocation();
    }
}
