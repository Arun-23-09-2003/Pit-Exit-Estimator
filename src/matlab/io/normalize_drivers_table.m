function drivers = normalize_drivers_table(drivers)
%NORMALIZE_DRIVERS_TABLE Ensure drivers table has consistent MATLAB types.

if isempty(drivers)
    return;
end

drivers.driver_number = double(drivers.driver_number);
drivers.car_index = double(drivers.car_index);
drivers.included_in_estimation = parse_logical_column(drivers.included_in_estimation);

if ismember("driver_code", drivers.Properties.VariableNames)
    drivers.driver_code = string(drivers.driver_code);
end
if ismember("team_name", drivers.Properties.VariableNames)
    drivers.team_name = string(drivers.team_name);
end
if ismember("exclusion_reason", drivers.Properties.VariableNames)
    drivers.exclusion_reason = string(drivers.exclusion_reason);
end

end

