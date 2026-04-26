function mode_name = mode_from_inputs(flags, drs_active)
%MODE_FROM_INPUTS Determine operating mode from flags and DRS command.
% flags = [is_in_pit_lane, is_under_sc, is_under_vsc]

is_in_pit_lane = logical(flags(1));
is_under_sc = logical(flags(2));
is_under_vsc = logical(flags(3));
drs_active = drs_active >= 0.5;

if is_in_pit_lane
    mode_name = "pit_mode";
elseif is_under_sc
    mode_name = "sc_mode";
elseif is_under_vsc
    mode_name = "vsc_mode";
elseif drs_active
    mode_name = "green_traffic_drs";
else
    mode_name = "green_free_air_no_drs";
end

end

