from pathlib import Path
import tempfile, unittest
from resono_runtime.skills.documents import AgentInstructionDocuments, AgentInstructionsError

class _Workspace:
    def __init__(self): self.registered=[]; self.removed=[]
    def register_managed(self, source, reference, **metadata): self.registered.append((source,reference,metadata))
    def remove_managed(self, reference): self.removed.append(reference)

class AgentInstructionDocumentsTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); root=Path(self.temporary.name); self.workspace=_Workspace()
        self.documents=AgentInstructionDocuments(voice_path=root/"voice"/"SKILLS.MD", background_path=root/"user"/"documents"/"SKILLS.MD", background_workspace=self.workspace)
    def tearDown(self): self.temporary.cleanup()
    def test_requires_exact_filename_and_one_destination(self):
        for filename in ("SKILL.md","skills.md","bundle.zip"):
            with self.assertRaisesRegex(AgentInstructionsError,"exactly SKILLS.MD"): self.documents.preflight(b"# Test",filename=filename,destination="voice")
        with self.assertRaisesRegex(AgentInstructionsError,"either Voice or Background"): self.documents.preflight(b"# Test",filename="SKILLS.MD",destination="both")
    def test_voice_injection_and_explicit_replacement(self):
        first=self.documents.preflight(b"# First",filename="SKILLS.MD",destination="voice"); self.documents.confirm(first.token,replace=False)
        self.assertIn("# First",self.documents.voice_instructions())
        second=self.documents.preflight(b"# Second",filename="SKILLS.MD",destination="voice"); self.assertEqual("conflict",second.state)
        with self.assertRaisesRegex(AgentInstructionsError,"explicit confirmation"): self.documents.confirm(second.token,replace=False)
    def test_background_is_registered_workspace_resource(self):
        pending=self.documents.preflight(b"# Background",filename="SKILLS.MD",destination="text"); item=self.documents.confirm(pending.token,replace=False)
        self.assertEqual("workspace://documents/SKILLS.MD",self.workspace.registered[-1][1]); self.assertEqual(b"# Background",item.path.read_bytes()); self.assertIn("workspace_read",self.documents.background_context())
