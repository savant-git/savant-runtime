#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


PALAVER_ROOT = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/"
    "_template/segue/innates/_template/segue/exiles/palaver"
)

CANONICAL_SERVER = PALAVER_ROOT / "runtime" / "server.py"
WEBUI_SERVER = PALAVER_ROOT / "apps" / "webui_ultra" / "server.py"

CANONICAL_BACKUP = CANONICAL_SERVER.with_suffix(
    ".py.pre-persona-ui"
)

WEBUI_BACKUP = WEBUI_SERVER.with_suffix(
    ".py.pre-persona-ui"
)

MARKER = "PALAVER_PERSONA_SELECTOR_V1"


class PatchError(RuntimeError):
    pass


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = text.count(old)

    if count != 1:
        raise PatchError(
            f"{label}: expected exactly one anchor, found {count}"
        )

    return text.replace(
        old,
        new,
        1,
    )


def atomic_write(
    path: Path,
    text: str,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.persona-ui-",
        dir=str(path.parent),
    )

    temporary = Path(
        temporary_name
    )

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                text
            )

            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temporary,
            path.stat().st_mode,
        )

        os.replace(
            temporary,
            path,
        )

    except Exception:
        temporary.unlink(
            missing_ok=True
        )
        raise


def patch_canonical_server(
    text: str,
) -> str:
    route_anchor = '''            "/api/chat",
            "/api/file/save",
'''

    route_replacement = '''            "/api/chat",
            "/api/persona/preference",
            "/api/file/save",
'''

    text = replace_once(
        text,
        route_anchor,
        route_replacement,
        "canonical POST route",
    )

    post_anchor = '''            if path == "/api/workspace/save":
'''

    preference_handler = '''            if path == "/api/persona/preference":
                try:
                    data = body_json(
                        self
                    )

                    if not isinstance(
                        data,
                        dict,
                    ):
                        raise RuntimeError(
                            "persona preference payload "
                            "must be an object"
                        )

                    state = dict(
                        _workspace_state(
                            legacy
                        )
                    )

                    requested = str(
                        data.get(
                            WORKSPACE_PERSONA_FIELD
                        )
                        or ""
                    ).strip()

                    if requested:
                        state[
                            WORKSPACE_PERSONA_FIELD
                        ] = _validate_persona_id(
                            legacy,
                            requested,
                        )
                    else:
                        state.pop(
                            WORKSPACE_PERSONA_FIELD,
                            None,
                        )

                    result = workspace_save(
                        state
                    )

                    workspace_persona = (
                        _workspace_persona_id(
                            legacy
                        )
                    )

                    send_json(
                        self,
                        {
                            "ok": True,
                            "result": result,
                            "workspace_persona": (
                                workspace_persona
                            ),
                            "effective_persona": (
                                workspace_persona
                                or DEFAULT_PERSONA_ID
                            ),
                            "default_persona": (
                                DEFAULT_PERSONA_ID
                            ),
                            "persona_owner": "envoy",
                            "workspace_owner": "palaver",
                        },
                    )
                    return

                except Exception as exc:
                    send_json(
                        self,
                        {
                            "ok": False,
                            "error": str(exc),
                        },
                        500,
                    )
                    return

            if path == "/api/workspace/save":
'''

    text = replace_once(
        text,
        post_anchor,
        preference_handler,
        "persona preference handler",
    )

    status_anchor = '''        "workspace_persona_preference_installed": (
            "/api/persona/preference"
            in canonical_routes()["get"]
            and "/api/workspace/save"
            in canonical_routes()["post"]
        ),
'''

    status_replacement = '''        "workspace_persona_preference_installed": (
            "/api/persona/preference"
            in canonical_routes()["get"]
            and "/api/persona/preference"
            in canonical_routes()["post"]
            and "/api/workspace/save"
            in canonical_routes()["post"]
        ),
'''

    text = replace_once(
        text,
        status_anchor,
        status_replacement,
        "compatibility status",
    )

    return text


def patch_webui_server(
    text: str,
) -> str:
    css_anchor = '''@media(max-width:1180px){html,body{overflow:auto}.app{height:auto;min-height:100vh}.top{height:auto;grid-template-columns:1fr;gap:12px}.status{justify-self:start}.nav{width:100%;overflow:auto;justify-content:flex-start}.shell{grid-template-columns:1fr}.card{min-height:320px}#chat{min-height:58vh}.msg{max-width:100%}.composer{grid-template-columns:1fr auto}.quick{grid-template-columns:1fr}}
'''

    css_replacement = '''/* PALAVER_PERSONA_SELECTOR_V1 */
.conversationHead{gap:12px}
.personaCtl{display:flex;align-items:center;gap:8px;min-width:0}
.personaCtl label{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.personaCtl select{max-width:220px;min-width:150px;padding:7px 28px 7px 10px;border-radius:12px;border:1px solid var(--line);background:#0b0d11;color:var(--cream);font:inherit;font-size:11px;outline:none}
.personaCtl select:focus{border-color:rgba(214,180,95,.62)}
.personaCtl select:disabled{opacity:.55}
.personaMeta{font-size:9px;color:var(--muted);white-space:nowrap}
@media(max-width:1180px){html,body{overflow:auto}.app{height:auto;min-height:100vh}.top{height:auto;grid-template-columns:1fr;gap:12px}.status{justify-self:start}.nav{width:100%;overflow:auto;justify-content:flex-start}.shell{grid-template-columns:1fr}.card{min-height:320px}#chat{min-height:58vh}.msg{max-width:100%}.composer{grid-template-columns:1fr auto}.quick{grid-template-columns:1fr}.personaCtl{flex-wrap:wrap}.personaCtl select{max-width:100%}}
'''

    text = replace_once(
        text,
        css_anchor,
        css_replacement,
        "persona selector CSS",
    )

    head_anchor = '''  <div class="cardHead"><b>Conversation</b><span>persistent</span></div>
'''

    head_replacement = '''  <div class="cardHead conversationHead">
    <b>Conversation</b>
    <div class="personaCtl">
      <label for="personaSelect">Persona</label>
      <select id="personaSelect" onchange="setPersonaPreference(this.value)" disabled>
        <option value="">Orobouros · default</option>
      </select>
      <span class="personaMeta" id="personaMeta">loading</span>
    </div>
  </div>
'''

    text = replace_once(
        text,
        head_anchor,
        head_replacement,
        "conversation header",
    )

    js_anchor = '''async function submitMsg(){const m=input.value.trim();if(!m)return;input.value="";await send(m)}
'''

    js_replacement = '''async function loadPersonaControl(){
 const select=document.getElementById("personaSelect");
 const meta=document.getElementById("personaMeta");
 if(!select||!meta)return;
 try{
  const [personasRes,prefRes]=await Promise.all([
   fetch("/api/personas"),
   fetch("/api/persona/preference")
  ]);
  const personasData=await personasRes.json();
  const prefData=await prefRes.json();
  if(!personasData.ok)throw new Error(personasData.error||"persona discovery failed");
  if(!prefData.ok)throw new Error(prefData.error||"persona preference failed");

  const defaultId=personasData.default_persona||prefData.default_persona||"orobouros";
  const workspaceId=prefData.workspace_persona||"";
  const rows=Array.isArray(personasData.personas)?personasData.personas:[];

  select.innerHTML="";

  const defaultOption=document.createElement("option");
  defaultOption.value="";
  defaultOption.textContent=(rows.find(x=>x.persona_id===defaultId)?.display_name||"Orobouros")+" · default";
  select.appendChild(defaultOption);

  for(const persona of rows){
   if(!persona||persona.persona_id===defaultId)continue;
   const option=document.createElement("option");
   option.value=persona.persona_id;
   option.textContent=persona.display_name||persona.persona_id;
   select.appendChild(option);
  }

  select.value=(workspaceId&&workspaceId!==defaultId)?workspaceId:"";
  meta.textContent=workspaceId?"workspace":"default";
  select.disabled=false;
 }catch(error){
  select.disabled=true;
  meta.textContent="unavailable";
  trace.textContent="persona UI: "+String(error);
 }
}

async function setPersonaPreference(value){
 const select=document.getElementById("personaSelect");
 const meta=document.getElementById("personaMeta");
 if(!select||!meta)return;

 select.disabled=true;
 meta.textContent="saving";

 try{
  const response=await fetch(
   "/api/persona/preference",
   {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
     persona_id:value||null
    })
   }
  );

  const data=await response.json();

  if(!data.ok){
   throw new Error(data.error||"persona preference save failed");
  }

  const defaultId=data.default_persona||"orobouros";
  const workspaceId=data.workspace_persona||"";

  select.value=(workspaceId&&workspaceId!==defaultId)?workspaceId:"";
  meta.textContent=workspaceId?"workspace":"default";
  trace.textContent="persona: "+(data.effective_persona||defaultId);
 }catch(error){
  meta.textContent="error";
  trace.textContent="persona preference: "+String(error);
  await loadPersonaControl();
 }finally{
  select.disabled=false;
 }
}

async function submitMsg(){const m=input.value.trim();if(!m)return;input.value="";await send(m)}
'''

    text = replace_once(
        text,
        js_anchor,
        js_replacement,
        "persona selector JavaScript",
    )

    script_end_anchor = '''document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();togglePalette(true)}if(e.key==="Escape")togglePalette(false)});
</script>
'''

    script_end_replacement = '''document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();togglePalette(true)}if(e.key==="Escape")togglePalette(false)});
loadPersonaControl();
</script>
'''

    text = replace_once(
        text,
        script_end_anchor,
        script_end_replacement,
        "persona selector startup",
    )

    return text


def main() -> int:
    canonical_text = CANONICAL_SERVER.read_text(
        encoding="utf-8"
    )

    webui_text = WEBUI_SERVER.read_text(
        encoding="utf-8"
    )

    if MARKER in webui_text:
        raise PatchError(
            "persona selector is already installed"
        )

    patched_canonical = patch_canonical_server(
        canonical_text
    )

    patched_webui = patch_webui_server(
        webui_text
    )

    if not CANONICAL_BACKUP.exists():
        shutil.copy2(
            CANONICAL_SERVER,
            CANONICAL_BACKUP,
        )

    if not WEBUI_BACKUP.exists():
        shutil.copy2(
            WEBUI_SERVER,
            WEBUI_BACKUP,
        )

    atomic_write(
        CANONICAL_SERVER,
        patched_canonical,
    )

    atomic_write(
        WEBUI_SERVER,
        patched_webui,
    )

    print(
        "PALAVER PERSONA UI PATCH: applied"
    )

    print(
        f"canonical_backup={CANONICAL_BACKUP}"
    )

    print(
        f"webui_backup={WEBUI_BACKUP}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
