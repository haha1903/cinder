# Copyright 2011 Denali Systems, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

from lxml import etree
import webob

from cinder.api.v2 import snapshots
from cinder import db
from cinder import exception
from cinder.openstack.common import log as logging
from cinder import test
from cinder.tests.api import fakes
from cinder.tests.api.v2 import stubs
from cinder import volume


LOG = logging.getLogger(__name__)

UUID = '00000000-0000-0000-0000-000000000001'
INVALID_UUID = '00000000-0000-0000-0000-000000000002'


def _get_default_snapshot_param():
    return {
        'id': UUID,
        'volume_id': 12,
        'status': 'available',
        'volume_size': 100,
        'created_at': None,
        'display_name': 'Default name',
        'display_description': 'Default description',
    }


def stub_snapshot_create(self, context,
                         volume_id, name,
                         description, metadata):
    snapshot = _get_default_snapshot_param()
    snapshot['volume_id'] = volume_id
    snapshot['display_name'] = name
    snapshot['display_description'] = description
    snapshot['metadata'] = metadata
    return snapshot


def stub_snapshot_delete(self, context, snapshot):
    if snapshot['id'] != UUID:
        raise exception.NotFound


def stub_snapshot_get(self, context, snapshot_id):
    if snapshot_id != UUID:
        raise exception.NotFound

    param = _get_default_snapshot_param()
    return param


def stub_snapshot_get_all(self, context, search_opts=None):
    param = _get_default_snapshot_param()
    return [param]


class SnapshotApiTest(test.TestCase):
    def setUp(self):
        super(SnapshotApiTest, self).setUp()
        self.controller = snapshots.SnapshotsController()

        self.stubs.Set(db, 'snapshot_get_all_by_project',
                       stubs.stub_snapshot_get_all_by_project)
        self.stubs.Set(db, 'snapshot_get_all',
                       stubs.stub_snapshot_get_all)

    def test_snapshot_create(self):
        self.stubs.Set(volume.api.API, "create_snapshot", stub_snapshot_create)
        self.stubs.Set(volume.api.API, 'get', stubs.stub_volume_get)
        snapshot_name = 'Snapshot Test Name'
        snapshot_description = 'Snapshot Test Desc'
        snapshot = {
            "volume_id": '12',
            "force": False,
            "name": snapshot_name,
            "description": snapshot_description
        }

        body = dict(snapshot=snapshot)
        req = fakes.HTTPRequest.blank('/v2/snapshots')
        resp_dict = self.controller.create(req, body)

        self.assertTrue('snapshot' in resp_dict)
        self.assertEqual(resp_dict['snapshot']['name'],
                         snapshot_name)
        self.assertEqual(resp_dict['snapshot']['description'],
                         snapshot_description)

    def test_snapshot_create_force(self):
        self.stubs.Set(volume.api.API, "create_snapshot_force",
                       stub_snapshot_create)
        self.stubs.Set(volume.api.API, 'get', stubs.stub_volume_get)
        snapshot_name = 'Snapshot Test Name'
        snapshot_description = 'Snapshot Test Desc'
        snapshot = {
            "volume_id": '12',
            "force": True,
            "name": snapshot_name,
            "description": snapshot_description
        }
        body = dict(snapshot=snapshot)
        req = fakes.HTTPRequest.blank('/v2/snapshots')
        resp_dict = self.controller.create(req, body)

        self.assertTrue('snapshot' in resp_dict)
        self.assertEqual(resp_dict['snapshot']['name'],
                         snapshot_name)
        self.assertEqual(resp_dict['snapshot']['description'],
                         snapshot_description)

        snapshot = {
            "volume_id": "12",
            "force": "**&&^^%%$$##@@",
            "name": "Snapshot Test Name",
            "description": "Snapshot Test Desc"
        }
        body = dict(snapshot=snapshot)
        req = fakes.HTTPRequest.blank('/v2/snapshots')
        self.assertRaises(exception.InvalidParameterValue,
                          self.controller.create,
                          req,
                          body)

    def test_snapshot_update(self):
        self.stubs.Set(volume.api.API, "get_snapshot", stub_snapshot_get)
        self.stubs.Set(volume.api.API, "update_snapshot",
                       stubs.stub_snapshot_update)
        updates = {
            "name": "Updated Test Name",
        }
        body = {"snapshot": updates}
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % UUID)
        res_dict = self.controller.update(req, UUID, body)
        expected = {
            'snapshot': {
                'id': UUID,
                'volume_id': 12,
                'status': 'available',
                'size': 100,
                'created_at': None,
                'name': 'Updated Test Name',
                'description': 'Default description',
                'metadata': {},
            }
        }
        self.assertEquals(expected, res_dict)

    def test_snapshot_update_missing_body(self):
        body = {}
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % UUID)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.update, req, UUID, body)

    def test_snapshot_update_invalid_body(self):
        body = {'name': 'missing top level snapshot key'}
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % UUID)
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.update, req, UUID, body)

    def test_snapshot_update_not_found(self):
        self.stubs.Set(volume.api.API, "get_snapshot", stub_snapshot_get)
        updates = {
            "name": "Updated Test Name",
        }
        body = {"snapshot": updates}
        req = fakes.HTTPRequest.blank('/v2/snapshots/not-the-uuid')
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.update, req,
                          'not-the-uuid', body)

    def test_snapshot_delete(self):
        self.stubs.Set(volume.api.API, "get_snapshot", stub_snapshot_get)
        self.stubs.Set(volume.api.API, "delete_snapshot", stub_snapshot_delete)

        snapshot_id = UUID
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % snapshot_id)
        resp = self.controller.delete(req, snapshot_id)
        self.assertEqual(resp.status_int, 202)

    def test_snapshot_delete_invalid_id(self):
        self.stubs.Set(volume.api.API, "delete_snapshot", stub_snapshot_delete)
        snapshot_id = INVALID_UUID
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % snapshot_id)
        self.assertRaises(webob.exc.HTTPNotFound, self.controller.delete,
                          req, snapshot_id)

    def test_snapshot_show(self):
        self.stubs.Set(volume.api.API, "get_snapshot", stub_snapshot_get)
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % UUID)
        resp_dict = self.controller.show(req, UUID)

        self.assertTrue('snapshot' in resp_dict)
        self.assertEqual(resp_dict['snapshot']['id'], UUID)

    def test_snapshot_show_invalid_id(self):
        snapshot_id = INVALID_UUID
        req = fakes.HTTPRequest.blank('/v2/snapshots/%s' % snapshot_id)
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.show, req, snapshot_id)

    def test_snapshot_detail(self):
        self.stubs.Set(volume.api.API, "get_all_snapshots",
                       stub_snapshot_get_all)
        req = fakes.HTTPRequest.blank('/v2/snapshots/detail')
        resp_dict = self.controller.detail(req)

        self.assertTrue('snapshots' in resp_dict)
        resp_snapshots = resp_dict['snapshots']
        self.assertEqual(len(resp_snapshots), 1)

        resp_snapshot = resp_snapshots.pop()
        self.assertEqual(resp_snapshot['id'], UUID)

    def test_snapshot_list_by_status(self):
        def stub_snapshot_get_all_by_project(context, project_id):
            return [
                stubs.stub_snapshot(1, display_name='backup1',
                                    status='available'),
                stubs.stub_snapshot(2, display_name='backup2',
                                    status='available'),
                stubs.stub_snapshot(3, display_name='backup3',
                                    status='creating'),
            ]
        self.stubs.Set(db, 'snapshot_get_all_by_project',
                       stub_snapshot_get_all_by_project)

        # no status filter
        req = fakes.HTTPRequest.blank('/v2/snapshots')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 3)
        # single match
        req = fakes.HTTPRequest.blank('/v2/snapshots?status=creating')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 1)
        self.assertEqual(resp['snapshots'][0]['status'], 'creating')
        # multiple match
        req = fakes.HTTPRequest.blank('/v2/snapshots?status=available')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 2)
        for snapshot in resp['snapshots']:
            self.assertEquals(snapshot['status'], 'available')
        # no match
        req = fakes.HTTPRequest.blank('/v2/snapshots?status=error')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 0)

    def test_snapshot_list_by_volume(self):
        def stub_snapshot_get_all_by_project(context, project_id):
            return [
                stubs.stub_snapshot(1, volume_id='vol1', status='creating'),
                stubs.stub_snapshot(2, volume_id='vol1', status='available'),
                stubs.stub_snapshot(3, volume_id='vol2', status='available'),
            ]
        self.stubs.Set(db, 'snapshot_get_all_by_project',
                       stub_snapshot_get_all_by_project)

        # single match
        req = fakes.HTTPRequest.blank('/v2/snapshots?volume_id=vol2')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 1)
        self.assertEqual(resp['snapshots'][0]['volume_id'], 'vol2')
        # multiple match
        req = fakes.HTTPRequest.blank('/v2/snapshots?volume_id=vol1')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 2)
        for snapshot in resp['snapshots']:
            self.assertEqual(snapshot['volume_id'], 'vol1')
        # multiple filters
        req = fakes.HTTPRequest.blank('/v2/snapshots?volume_id=vol1'
                                      '&status=available')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 1)
        self.assertEqual(resp['snapshots'][0]['volume_id'], 'vol1')
        self.assertEqual(resp['snapshots'][0]['status'], 'available')

    def test_snapshot_list_by_name(self):
        def stub_snapshot_get_all_by_project(context, project_id):
            return [
                stubs.stub_snapshot(1, display_name='backup1'),
                stubs.stub_snapshot(2, display_name='backup2'),
                stubs.stub_snapshot(3, display_name='backup3'),
            ]
        self.stubs.Set(db, 'snapshot_get_all_by_project',
                       stub_snapshot_get_all_by_project)

        # no name filter
        req = fakes.HTTPRequest.blank('/v2/snapshots')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 3)
        # filter by one name
        req = fakes.HTTPRequest.blank('/v2/snapshots?name=backup2')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 1)
        self.assertEquals(resp['snapshots'][0]['name'], 'backup2')
        # filter no match
        req = fakes.HTTPRequest.blank('/v2/snapshots?name=backup4')
        resp = self.controller.index(req)
        self.assertEqual(len(resp['snapshots']), 0)

    def test_admin_list_snapshots_limited_to_project(self):
        req = fakes.HTTPRequest.blank('/v2/fake/snapshots',
                                      use_admin_context=True)
        res = self.controller.index(req)

        self.assertTrue('snapshots' in res)
        self.assertEqual(1, len(res['snapshots']))

    def test_list_snapshots_with_limit_and_offset(self):
        def list_snapshots_with_limit_and_offset(is_admin):
            def stub_snapshot_get_all_by_project(context, project_id):
                return [
                    stubs.stub_snapshot(1, display_name='backup1'),
                    stubs.stub_snapshot(2, display_name='backup2'),
                    stubs.stub_snapshot(3, display_name='backup3'),
                ]

            self.stubs.Set(db, 'snapshot_get_all_by_project',
                           stub_snapshot_get_all_by_project)

            req = fakes.HTTPRequest.blank('/v2/fake/snapshots?limit=1\
                                          &offset=1',
                                          use_admin_context=is_admin)
            res = self.controller.index(req)

            self.assertTrue('snapshots' in res)
            self.assertEqual(1, len(res['snapshots']))
            self.assertEqual(2, res['snapshots'][0]['id'])

        #admin case
        list_snapshots_with_limit_and_offset(is_admin=True)
        #non_admin case
        list_snapshots_with_limit_and_offset(is_admin=False)

    def test_admin_list_snapshots_all_tenants(self):
        req = fakes.HTTPRequest.blank('/v2/fake/snapshots?all_tenants=1',
                                      use_admin_context=True)
        res = self.controller.index(req)
        self.assertTrue('snapshots' in res)
        self.assertEqual(3, len(res['snapshots']))

    def test_all_tenants_non_admin_gets_all_tenants(self):
        req = fakes.HTTPRequest.blank('/v2/fake/snapshots?all_tenants=1')
        res = self.controller.index(req)
        self.assertTrue('snapshots' in res)
        self.assertEqual(1, len(res['snapshots']))

    def test_non_admin_get_by_project(self):
        req = fakes.HTTPRequest.blank('/v2/fake/snapshots')
        res = self.controller.index(req)
        self.assertTrue('snapshots' in res)
        self.assertEqual(1, len(res['snapshots']))

    def _create_snapshot_bad_body(self, body):
        req = fakes.HTTPRequest.blank('/v2/fake/snapshots')
        req.method = 'POST'

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.create, req, body)

    def test_create_no_body(self):
        self._create_snapshot_bad_body(body=None)

    def test_create_missing_snapshot(self):
        body = {'foo': {'a': 'b'}}
        self._create_snapshot_bad_body(body=body)

    def test_create_malformed_entity(self):
        body = {'snapshot': 'string'}
        self._create_snapshot_bad_body(body=body)


class SnapshotSerializerTest(test.TestCase):
    def _verify_snapshot(self, snap, tree):
        self.assertEqual(tree.tag, 'snapshot')

        for attr in ('id', 'status', 'size', 'created_at',
                     'name', 'description', 'volume_id'):
            self.assertEqual(str(snap[attr]), tree.get(attr))

    def test_snapshot_show_create_serializer(self):
        serializer = snapshots.SnapshotTemplate()
        raw_snapshot = dict(
            id='snap_id',
            status='snap_status',
            size=1024,
            created_at=datetime.datetime.now(),
            name='snap_name',
            description='snap_desc',
            display_description='snap_desc',
            volume_id='vol_id',
        )
        text = serializer.serialize(dict(snapshot=raw_snapshot))

        print text
        tree = etree.fromstring(text)

        self._verify_snapshot(raw_snapshot, tree)

    def test_snapshot_index_detail_serializer(self):
        serializer = snapshots.SnapshotsTemplate()
        raw_snapshots = [
            dict(
                id='snap1_id',
                status='snap1_status',
                size=1024,
                created_at=datetime.datetime.now(),
                name='snap1_name',
                description='snap1_desc',
                volume_id='vol1_id',
            ),
            dict(
                id='snap2_id',
                status='snap2_status',
                size=1024,
                created_at=datetime.datetime.now(),
                name='snap2_name',
                description='snap2_desc',
                volume_id='vol2_id',
            )
        ]
        text = serializer.serialize(dict(snapshots=raw_snapshots))

        print text
        tree = etree.fromstring(text)

        self.assertEqual('snapshots', tree.tag)
        self.assertEqual(len(raw_snapshots), len(tree))
        for idx, child in enumerate(tree):
            self._verify_snapshot(raw_snapshots[idx], child)
