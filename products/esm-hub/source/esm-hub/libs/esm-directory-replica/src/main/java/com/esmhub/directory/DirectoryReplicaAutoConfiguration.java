package com.esmhub.directory;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.AutoConfigurationPackage;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import tools.jackson.databind.json.JsonMapper;

/** Enables the replica (entities, repositories, listeners, lookup). Disable with esm.directory.replica.enabled=false. */
@AutoConfiguration
@AutoConfigurationPackage(basePackages = "com.esmhub.directory")
@ConditionalOnProperty(name = "esm.directory.replica.enabled", havingValue = "true", matchIfMissing = true)
public class DirectoryReplicaAutoConfiguration {

    @Bean
    DirectoryReplicaListener directoryReplicaListener(JsonMapper mapper, DirUserRepository users,
                                                      DirTeamRepository teams,
                                                      DirServiceRepository services,
                                                      DirOfficeRepository offices) {
        return new DirectoryReplicaListener(mapper, users, teams, services, offices);
    }

    @Bean
    DirectoryLookup directoryLookup(DirUserRepository users, DirTeamRepository teams,
                                    DirServiceRepository services, DirOfficeRepository offices) {
        return new DirectoryLookup(users, teams, services, offices);
    }
}
