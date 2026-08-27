from runtime.constitution.platform import subsystem_entrypoint
def entrypoint(): return subsystem_entrypoint("service:voice","runtime.envoy.voice_engine")
