package com.esmhub.asset.service.asset;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

public interface AssetRepository extends JpaRepository<Asset, Long>, JpaSpecificationExecutor<Asset> {
    Optional<Asset> findByIdAndCompanyId(Long id, long companyId);

    boolean existsByCompanyIdAndAssetTagIgnoreCase(long companyId, String assetTag);

    boolean existsByCompanyIdAndSerialNumber(long companyId, String serialNumber);
}
