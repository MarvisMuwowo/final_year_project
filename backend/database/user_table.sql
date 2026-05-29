create type user_role as enum('system_admin','security_analyst');
create table users(
  id serial primary key,
  username varchar(100) not null unique,
  password_hash varchar(255) not null,
  role user_role default 'security_analyst',
  last_login timestamp null default null,
  created_at timestamp default now(),
  is_active boolean default true
);


alter table users add column email varchar(100);
alter table users alter column email set not null;
alter table users add constraint users_email_unique unique(email);
alter table users add constraint email_format_check check(email~*'^[A-Za-z0-9._%+-]+@[A-Zaz0-9.-]+\.[A-Za-z]{2,}$');
