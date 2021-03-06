# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from gettext import gettext as _

from pulp.client.extensions.extensions import PulpCliFlag


FLAG_NO_COMMIT = PulpCliFlag('--no-commit', _('test the transaction without committing it'))

FLAG_REBOOT = PulpCliFlag('--reboot', _('reboot after a successful transaction'))

FLAG_IMPORT_KEYS = PulpCliFlag('--import-keys', _('import GPG keys as needed'))

FLAG_ALL_CONTENT = PulpCliFlag('--all', _('update all content units'), ['-a'])
