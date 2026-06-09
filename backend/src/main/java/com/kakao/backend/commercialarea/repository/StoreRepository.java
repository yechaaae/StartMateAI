package com.kakao.backend.commercialarea.repository;

import com.kakao.backend.commercialarea.domain.Store;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StoreRepository extends JpaRepository<Store, Long> {

    Optional<Store> findBySourceAndSourceStoreId(String source, String sourceStoreId);

    List<Store> findBySido(String sido);

    List<Store> findBySidoAndSigungu(String sido, String sigungu);

    List<Store> findBySidoAndSigunguAndDong(String sido, String sigungu, String dong);
}
