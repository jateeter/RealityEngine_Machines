import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_device_templates import ROOT,render,check,UA,DI

class DeviceTemplateTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name)
        (r/'assets').mkdir()
        for name in ['opcua-source-receipt.json','device-class-catalog.json']:shutil.copyfile(ROOT/'assets'/name,r/'assets'/name)
        shutil.copytree(ROOT/'intake/opcua-di',r/'intake/opcua-di');return r
    def mutate(self,r,name,fn):
        p=r/'assets'/name;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))
    def test_complete_di_type_inventory_and_exact_dependency(self):
        self.assertEqual(check(ROOT),[]);d=render(ROOT)
        self.assertEqual(len(d['templates']),58);self.assertEqual(len(d['declarations']),447)
        self.assertTrue(d['coreDependencyEditionMatched']);self.assertEqual(d['models'][UA]['Version'],'1.05.04')
        self.assertEqual(d['typeCounts'],{'UAObjectType':42,'UAVariableType':2,'UADataType':9,'UAReferenceType':5})
        self.assertTrue(all(t['integrationContextStandardId']=='OP23' for t in d['templates']))
    def test_namespace_identity_and_abstract_device_preserved(self):
        d=render(ROOT)
        self.assertNotEqual(d['declarations'][DI+'|i=1']['attributes']['BrowseName'],d['supportingCoreDefinitions'][UA+'|i=1']['attributes']['BrowseName'])
        device=next(t for t in d['templates'] if t['browseName']=='1:DeviceType')
        self.assertTrue(device['isAbstract']);self.assertTrue(device['declaredMandatoryMemberKeys'])
        self.assertTrue(device['ancestorTypeKeys']);self.assertEqual(device['instanceRequirements']['controlAction'],'DENY')
    def test_missing_type_rejected(self):
        r=self.fixture();self.mutate(r,'device-class-catalog.json',lambda d:d['templates'].pop());self.assertTrue(check(r))
    def test_false_concrete_type_rejected(self):
        r=self.fixture();self.mutate(r,'device-class-catalog.json',lambda d:next(t for t in d['templates'] if t['browseName']=='1:DeviceType').update(isAbstract=False));self.assertTrue(check(r))
    def test_lost_mandatory_members_rejected(self):
        r=self.fixture();self.mutate(r,'device-class-catalog.json',lambda d:next(t for t in d['templates'] if t['browseName']=='1:DeviceType')['declaredMandatoryMemberKeys'].clear());self.assertTrue(check(r))
    def test_invented_core_version_rejected(self):
        r=self.fixture();self.mutate(r,'opcua-source-receipt.json',lambda d:d['files'][1]['model'].update(Version='1.05.07'));self.assertTrue(check(r))
    def test_source_mutation_rejected(self):
        r=self.fixture();p=r/'intake/opcua-di/Opc.Ua.Di.NodeSet2.xml';p.write_bytes(p.read_bytes()+b'changed');self.assertTrue(check(r))
    def test_unsupported_execution_claim_rejected(self):
        r=self.fixture();self.mutate(r,'device-class-catalog.json',lambda d:d['templates'][0]['instanceRequirements'].update(controlAction='ALLOW'));self.assertTrue(check(r))
    def test_false_normative_completion_rejected(self):
        r=self.fixture();self.mutate(r,'device-class-catalog.json',lambda d:d.update(normativeCoverageComplete=True));self.assertTrue(check(r))
    def test_unlisted_source_rejected(self):
        r=self.fixture();(r/'intake/opcua-di/extra.xml').write_text('<unreviewed/>');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
