package com.esmhub.change.service;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class ChangeServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(ChangeServiceApplication.class, args);
    }
}
