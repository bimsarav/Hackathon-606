package com.esmhub.directory.service;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class DirectoryServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(DirectoryServiceApplication.class, args);
    }
}
