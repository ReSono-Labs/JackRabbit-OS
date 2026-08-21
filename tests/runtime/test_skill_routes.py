from pathlib import Path
import tempfile, unittest
from resono_runtime.api.skill_routes import SkillRoutes
from resono_runtime.security.pairing import PairingAuthority
from resono_runtime.skills.documents import AgentInstructionDocuments
class _Workspace:
    def register_managed(self,*args,**kwargs): pass
    def remove_managed(self,*args,**kwargs): pass
class SkillRoutesTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); root=Path(self.temporary.name)
        self.routes=SkillRoutes(AgentInstructionDocuments(voice_path=root/'voice'/'SKILLS.MD',background_path=root/'user'/'documents'/'SKILLS.MD',background_workspace=_Workspace())); self.pairing=PairingAuthority()
    def tearDown(self): self.temporary.cleanup()
    def test_preflight_and_confirm_one_voice_document(self):
        request=_Request('/v1/management/skills/preflight',raw=b'# Voice',headers={'X-ReSono-Skill-Filename':'SKILLS.MD','X-ReSono-Agent-Audience':'voice','Content-Type':'text/markdown'})
        self.assertTrue(self.routes.handle_post(request,self.pairing)); self.assertEqual(200,request.status)
        confirm=_Request('/v1/management/skills/confirm',json_body={'preflightToken':request.payload['preflightToken'],'replace':False})
        self.routes.handle_post(confirm,self.pairing); self.assertEqual(201,confirm.status); self.assertEqual('voice',confirm.payload['name'])
    def test_unknown_route_is_not_claimed(self): self.assertFalse(self.routes.handle_get(_Request('/v1/management/other'),self.pairing))
class _Request:
    def __init__(self,path,*,raw=None,json_body=None,headers=None): self.path=path; self.headers=headers or {}; self._raw=raw; self._json=json_body; self.status=None; self.payload=None
    def respond_json(self,status,payload,**kwargs): self.status=status; self.payload=payload
    def browser_session(self,authority,*,mutation): return object()
    def request_json(self,*,max_bytes=4096): return self._json
    def request_bytes(self,*,max_bytes): return self._raw
if __name__=='__main__': unittest.main()
