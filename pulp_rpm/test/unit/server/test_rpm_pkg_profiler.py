# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock
import os
import random
import shutil
import sys
import tempfile
import unittest
import yum
from pulp.plugins.model import Consumer, Repository, Unit
from pulp.server.managers import factory
from pulp.server.managers.consumer.cud import ConsumerManager

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/profilers/")
from pulp_rpm.common.ids import TYPE_ID_PROFILER_RPM_PKG, TYPE_ID_RPM, UNIT_KEY_RPM
from pulp_rpm.yum_plugin import comps_util, util, updateinfo

import profiler_mocks
import rpm_support_base
from rpm_pkg_profiler.profiler import RPMPkgProfiler

class TestRpmPkgProfiler(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestRpmPkgProfiler, self).setUp()
        self.data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data")
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
        self.consumer_id = "test_errata_profiler_consumer_id"
        self.profiles = self.get_test_profile()
        self.test_consumer = Consumer(self.consumer_id, self.profiles)
        # i386 version of consumer to test arch issues
        self.consumer_id_i386 = "%s.i386" % (self.consumer_id)
        self.profiles_i386 = self.get_test_profile(arch="i386")
        self.test_consumer_i386 = Consumer(self.consumer_id_i386, self.profiles_i386)
        # consumer has been updated, and has the updated rpms installed
        self.consumer_id_been_updated = "%s.been_updated" % (self.consumer_id)
        self.profiles_been_updated = self.get_test_profile_been_updated()
        self.test_consumer_been_updated = Consumer(self.consumer_id_been_updated, self.profiles_been_updated)

    def tearDown(self):
        super(TestRpmPkgProfiler, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def create_rpm_dict(self, name, epoch, version, release, arch, checksum, checksumtype):
        unit_key = {"name":name, "epoch":epoch, "version":version, "release":release, 
                "arch":arch, "checksum":checksum, "checksumtype":checksumtype}
        return {"unit-key":unit_key}

    def create_profile_entry(self, name, epoch, version, release, arch, vendor):
        return {"name":name, "epoch": epoch, "version":version, "release":release, 
                "arch":arch, "vendor":vendor}

    def get_test_profile(self, arch="x86_64"):
        foo = self.create_profile_entry("emoticons", 0, "0.0.1", "1", arch, "Test Vendor")
        bar = self.create_profile_entry("patb", 0, "0.0.1", "1", arch, "Test Vendor")
        return {TYPE_ID_RPM:[foo, bar]}

    def get_test_profile_been_updated(self, arch="x86_64"):
        foo = self.create_profile_entry("emoticons", 0, "0.1", "2", arch, "Test Vendor")
        bar = self.create_profile_entry("patb", 0, "0.1", "2", arch, "Test Vendor")
        return {TYPE_ID_RPM:[foo, bar]}

    def test_metadata(self):
        data = RPMPkgProfiler.metadata()
        self.assertTrue(data.has_key("id"))
        self.assertEquals(data['id'], TYPE_ID_PROFILER_RPM_PKG)
        self.assertTrue(data.has_key("display_name"))
        self.assertTrue(data.has_key("types"))
        self.assertTrue(TYPE_ID_RPM in data["types"])

    def test_rpm_applicable_to_consumer(self):
        rpm = {}
        prof = RPMPkgProfiler()
        applicable, old_rpm = prof.rpm_applicable_to_consumer(Consumer("test", {}), rpm)
        self.assertEqual(applicable, False)
        self.assertEqual(old_rpm, {})

        # Test with newer RPM
        #  The consumer has already been configured with a profile containing 'emoticons'
        rpm = self.create_profile_entry("emoticons", 0, "0.1", "2", "x86_64", "Test Vendor")
        applicable, old_rpm = prof.rpm_applicable_to_consumer(self.test_consumer, rpm)
        self.assertTrue(applicable)
        self.assertTrue(old_rpm)
        self.assertTrue(old_rpm.has_key("emoticons x86_64"))
        self.assertEqual("emoticons", old_rpm["emoticons x86_64"]["installed"]["name"])
        self.assertEqual("0.0.1", old_rpm["emoticons x86_64"]["installed"]["version"])

    def test_unit_applicable_true(self):
        rpm_unit_key = self.create_profile_entry("emoticons", 0, "0.1", "2", "x86_64", "Test Vendor")
        rpm_unit = Unit(TYPE_ID_RPM, rpm_unit_key, {}, None)
        existing_units = [rpm_unit]
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_rpms = [rpm_unit.unit_key]

        prof = RPMPkgProfiler()
        report_list = prof.units_applicable(self.test_consumer, ["test_repo_id"], TYPE_ID_RPM, example_rpms, None, conduit)
        self.assertFalse(report_list == [])

    def test_unit_applicable_same_name_diff_arch(self):
        rpm_unit_key = self.create_profile_entry("emoticons", 0, "0.1", "2", "x86_64", "Test Vendor")
        rpm_unit = Unit(TYPE_ID_RPM, rpm_unit_key, {}, None)
        existing_units = [rpm_unit]
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_rpms = [rpm_unit.unit_key]

        prof = RPMPkgProfiler()
        report_list = prof.units_applicable(self.test_consumer_i386, ["test_repo_id"], TYPE_ID_RPM, example_rpms, None, conduit)
        self.assertTrue(report_list == [])

    def test_unit_applicable_updated_rpm_already_installed(self):
        rpm_unit_key = self.create_profile_entry("emoticons", 0, "0.1", "2", "x86_64", "Test Vendor")
        rpm_unit = Unit(TYPE_ID_RPM, rpm_unit_key, {}, None)
        existing_units = [rpm_unit]
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_rpms = [rpm_unit.unit_key]

        prof = RPMPkgProfiler()
        report_list = prof.units_applicable(self.test_consumer_been_updated, ["test_repo_id"], TYPE_ID_RPM, example_rpms, None, conduit)
        self.assertTrue(report_list == [])

    def test_unit_applicable_false(self):
        rpm_unit_key = self.create_profile_entry("bla-bla", 0, "0.1", "2", "x86_64", "Test Vendor")
        rpm_unit = Unit(TYPE_ID_RPM, rpm_unit_key, {}, None)
        existing_units = [rpm_unit]
        test_repo = profiler_mocks.get_repo("test_repo_id")
        conduit = profiler_mocks.get_profiler_conduit(existing_units=existing_units, repo_bindings=[test_repo])
        example_rpms = [rpm_unit.unit_key]

        prof = RPMPkgProfiler()
        report_list = prof.units_applicable(self.test_consumer_i386, ["test_repo_id"], TYPE_ID_RPM, example_rpms, None, conduit)
        self.assertTrue(report_list == [])

