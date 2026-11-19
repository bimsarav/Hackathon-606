package com.esmhub.asset.service.asset;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AssetAssignmentRepository extends JpaRepository<AssetAssignment, Long> {
    List<AssetAssignment> findByAssetIdOrderByAssignedAtDescIdDesc(long assetId);

    Optional<AssetAssignment> findByAssetIdAndReturnedAtIsNull(long assetId);
}
