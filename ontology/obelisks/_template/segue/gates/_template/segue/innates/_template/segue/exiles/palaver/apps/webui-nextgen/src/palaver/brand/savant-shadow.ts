import {ShadowMaterial} from "three"
export function shadowReceiverMaterial() {
  const material = new ShadowMaterial({
    opacity: 0.32, transparent: true, depthWrite: false,
  })
  material.onBeforeCompile = shader => {
    if (!shader.vertexShader.includes("#include <common>") ||
        !shader.vertexShader.includes("#include <begin_vertex>") ||
        !shader.vertexShader.includes("#include <shadowmap_vertex>") ||
        !shader.fragmentShader.includes("#include <common>") ||
        !shader.fragmentShader.includes("#include <fog_fragment>")) return
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vSavantShadow;\n")
      .replace("#include <begin_vertex>",
        "#include <begin_vertex>\nvSavantShadow = position.xy / 5.0 + 0.5;\n")
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vSavantShadow;\n")
      .replace("#include <fog_fragment>",
        `gl_FragColor.a *= smoothstep(0.0, 0.42, vSavantShadow.y)
          * smoothstep(0.0, 0.14, vSavantShadow.x)
          * (1.0 - smoothstep(0.86, 1.0, vSavantShadow.x));
        #include <fog_fragment>`)
  }
  material.customProgramCacheKey = () => "savant-logo-diagonal-shadow-v1"
  return material
}
