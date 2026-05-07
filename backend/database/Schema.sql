create table alert_logs(
    id serial primary key,

    --core alert metadata
    event_timestamp timestamp not null,
    protocol varchar(20),
    source_port integer,
    packet_length integer,

    --Anonymized network identifiers
    source_ip_hash text not null,
    destination_ip_hash  text not null,
    source_is_internal boolean,
    destination_is_internal boolean,

    --Traffic cotext
    traffic_type varchar(50),
    attack_type varchar(100),
    attack_signature text,

    --ML related features
    anomaly_score double precision,
    malware_indicator text,

    severity_level varchar(10) check(severity_level in('Low','Medium', 'High')),
    log_source varchar(50),
    network_segment varchar(100),

    created_at timestamp default 
    current_timestamp
);

