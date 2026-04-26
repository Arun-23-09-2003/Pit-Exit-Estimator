function m = mode_params(cfg, mode_name)
%MODE_PARAMS Return mode-specific parameter struct.

if ~isfield(cfg.mode, mode_name)
    error("Unknown mode: %s", mode_name);
end
m = cfg.mode.(mode_name);

end

