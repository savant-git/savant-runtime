from pathlib import Path
import unittest

from runtime.constitution import (ConstitutionalPlatform,FUTURE_ATTACHMENT_POINTS,HealthState,
    LifecyclePhase,LifecycleTracker,LifecycleTransitionError)

ROOT=Path(__file__).resolve().parents[2]
PLUGIN=ROOT/"tests/constitution/demo_platform_plugin.py"

class Phase6PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.platform=ConstitutionalPlatform.start(ROOT,(PLUGIN,))

    def test_every_service_has_exactly_one_entrypoint(self):
        identities=[s.identity for s in self.platform.subsystems]
        self.assertEqual(9,len(identities)); self.assertEqual(len(identities),len(set(identities)))
        self.assertTrue({o.id for o in self.platform.registry.by_kind("service")} <= set(identities))
        for subsystem in self.platform.subsystems:
            for stage in ("discover","validate","register","bootstrap","project","shutdown","health","diagnostics","migration"):
                self.assertTrue(callable(getattr(subsystem,stage)))

    def test_lifecycle_is_deterministic_and_illegal_transitions_fail(self):
        tracker=LifecycleTracker(("x",))
        with self.assertRaises(LifecycleTransitionError): tracker.transition("x",LifecyclePhase.ACTIVE)
        self.assertEqual(LifecyclePhase.ACTIVE,self.platform.lifecycle.get("reality"))

    def test_capabilities_are_discovered_queryable_and_composable(self):
        capability=self.platform.capability("service:voice"); self.assertEqual("1.0.0",capability.version)
        composed=self.platform.compose_capabilities("service:voice","service:lineage")
        self.assertIn("operator:voice-engine",composed.operators); self.assertIn("operator:lineage-graph",composed.operators)

    def test_bus_health_diagnostics_and_metrics(self):
        received=[]; unsubscribe=self.platform.bus.subscribe("diagnostic",received.append)
        diagnostic=self.platform.diagnose_dependency("service:voice","exile:envoy","verification failure")
        unsubscribe(); self.assertEqual("dependency_failed",diagnostic.code); self.assertTrue(diagnostic.authority_chain)
        self.assertTrue(diagnostic.lineage); self.assertTrue(diagnostic.provenance); self.assertEqual(1,len(received))
        self.assertEqual(HealthState.HEALTHY,self.platform.health("service:voice").state)
        self.platform.traverse_dependencies("service:voice")
        self.assertTrue({"bootstrap","discovery","validation","projection","dependency_traversal"} <= {m.name for m in self.platform.metrics()})

    def test_projection_rejection_is_diagnostic(self):
        with self.assertRaises(ValueError): self.platform.project("missing-target","service:voice")
        self.assertTrue(any(d.code=="projection_rejected" for d in self.platform.diagnostics("service:voice")))

    def test_plugin_is_external_and_future_interfaces_are_reserved(self):
        self.assertEqual("External verification capability.",self.platform.registry.get("service:demonstration-plugin").description)
        self.assertEqual(len(FUTURE_ATTACHMENT_POINTS),18)
        for name in FUTURE_ATTACHMENT_POINTS: self.assertIsNotNone(self.platform.attachment_interface(name))

if __name__=="__main__": unittest.main()
