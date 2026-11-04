from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from private_files import AccessError, SshFiles
from private_transaction import Transactions
import android_access


class SshFilesTests(unittest.TestCase):
    def test_pinned_noninteractive_transport_with_no_forwarding_or_host_shell(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0,
            b'/data/user/0/com.guille.spring/files\n10123\n10123:10123\nrw\n', b''))
        store = SshFiles('app@android-test', port=2222, runner=runner)
        store.verify()
        command = runner.call_args.args[0]
        for flag in ('BatchMode=yes', 'StrictHostKeyChecking=yes', 'ClearAllForwardings=yes', 'ControlPath=none', 'ForwardAgent=no', 'PermitLocalCommand=no'):
            self.assertIn(flag, command)
        self.assertNotIn('StrictHostKeyChecking=no', command)
        self.assertEqual(command[-2], 'app@android-test'); self.assertIn('2222', command)
        self.assertEqual(shlex.split(command[-1])[:2], ['sh', '-c'])
        self.assertFalse(runner.call_args.kwargs['shell'])
        runner.return_value = subprocess.CompletedProcess([], 0, b'\x00\xff\r\n', b'')
        self.assertEqual(store.read('ruby/binary'), b'\x00\xff\r\n')
        with tempfile.TemporaryDirectory() as name:
            tx = Transactions(store, Path(name))
            self.assertEqual(tx.target['kind'], 'ssh'); self.assertEqual(tx.target['host'], 'app@android-test')

    def test_invalid_hosts_and_missing_server_fail_without_password_or_key_acceptance(self):
        for host in ('-oProxyCommand=bad', '-a@host', 'host;command', 'host\ncommand', 'user@host:22', '', 'host/path'):
            with self.subTest(host=host), self.assertRaises(ValueError): SshFiles(host)
        runner = Mock(side_effect=OSError('host key not trusted'))
        store = SshFiles('android-test', runner=runner)
        with self.assertRaises(AccessError): store.verify()
        self.assertIsNone(store.identity)

    def test_access_cli_reports_ssh_without_claiming_deployment(self):
        store = Mock(); store.verify.return_value = {'uid': 10123, 'access': 'shell'}
        output = io.StringIO()
        with patch.object(android_access, 'SshFiles', return_value=store), redirect_stdout(output):
            android_access.main(['--ssh-host', 'fixture-only'])
        info = json.loads(output.getvalue())
        self.assertFalse(info['androidDeploymentVerified']); self.assertFalse(info['writeRoundTrip'])
        store.verify.assert_called_once()
