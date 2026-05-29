create table classifications (
id serial primary key,
event_id int not null,
user_id int null,
predicted_label varchar(100) not null,
confidence_score real not null check (confidence_score>=0 and confidence_score<=1),
classified_at timestamp default current_timestamp,
constraint fk_user foreign key (user_id) references users(id) on delete set null,
constraint fk_log foreign key (event_id) references events(id) on delete cascade
);