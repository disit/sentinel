USE checker;

ALTER TABLE `checker`.`cronjob_history` 
CHANGE COLUMN `result` `result` VARCHAR(4000) NOT NULL ,
CHANGE COLUMN `errors` `errors` VARCHAR(4000) NULL DEFAULT NULL ;
