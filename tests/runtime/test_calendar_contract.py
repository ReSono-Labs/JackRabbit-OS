from __future__ import annotations
from datetime import UTC,datetime,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from resono_runtime.agents import AgentKind
from resono_runtime.domains.calendar import CalendarAccountConfiguration,CalendarAccountLimitError,CalendarCapabilityDenied,CalendarEvent,CalendarRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.tools import ToolCatalog,ToolInvocationResult
from resono_runtime.tools.calendar import CalendarToolPackage

class CalendarContractTest(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.db=RuntimeDatabase(Path(self.tmp.name)/"runtime.sqlite3");self.db.migrate();self.repo=CalendarRepository(self.db)
 def tearDown(self):self.tmp.cleanup()
 def test_two_accounts_and_upcoming_only(self):
  accounts=[self.account(str(i)) for i in range(2)]
  with self.assertRaises(CalendarAccountLimitError):self.account("third")
  now=datetime.now(UTC);account=accounts[0].configuration.account_id
  self.repo.replace_account_events(account,(self.event(account,"past",now-timedelta(days=2),now-timedelta(days=1)),self.event(account,"current",now-timedelta(minutes=5),now+timedelta(minutes=5)),self.event(account,"future",now+timedelta(hours=1),now+timedelta(hours=2))))
  self.assertEqual(["current","future"],[item.title for item in self.repo.upcoming_events(now.isoformat())])
 def test_read_only_denies_mutation(self):
  account=self.account("read only")
  with self.assertRaises(CalendarCapabilityDenied):self.repo.require_capability(account.configuration.account_id,"create")
 def test_complete_tool_package(self):
  catalog=ToolCatalog();CalendarToolPackage(_ToolService()).register(catalog)
  self.assertEqual({"calendar_list_upcoming","calendar_search","calendar_read_event","calendar_create_event","calendar_update_event","calendar_delete_event","calendar_confirm_action"},{item["name"] for item in catalog.mcp_definitions(AgentKind.VOICE)})
 def account(self,label):return self.repo.create_account(CalendarAccountConfiguration(str(uuid4()),"ics_subscription",label,"https://example.com/calendar.ics",None),None)
 @staticmethod
 def event(account,title,start,end):return CalendarEvent(str(uuid4()),account,title,"",title,start.isoformat(),end.isoformat(),"UTC",False,None,"Calendar",None,None,"confirmed",False,None,datetime.now(UTC).isoformat())
class _ToolService:
 def invoke_tool(self,name,context,arguments):return ToolInvocationResult("ok")
if __name__=="__main__":unittest.main()
