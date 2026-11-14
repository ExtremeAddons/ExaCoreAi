#   #
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version
#    of the License, or (at your option) any later version.
#   #
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#   #
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software Foundation,
#    Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#   #
#   Copyright 2019 2026(C) Andrea Donati
#


from .installation_validator import ServiceValidator
import os
import bpy


class Draw:
    # Variabile di classe per mantenere lo stato del menu a tendina aperto/chiuso finché l'addon è attivo
    show_details_state = False

    def __init__(self, extreme_addons_path):
        """Initialize the Draw class with the path to the service configuration and the extreme addons' path.
        :param extreme_addons_path: The path to the extreme addons directory."""

        self.local_config_path = os.path.join(os.path.dirname(__file__), "../local_config.json")
        self.service_config_path = os.path.join(os.path.dirname(__file__), "../service_config.json")

        installation_ok = ServiceValidator(extreme_addons_path).is_installed()
        if installation_ok:
            self.r_list = ServiceValidator(self.local_config_path).get_resource_lists()
        else:
            self.r_list = ServiceValidator(self.service_config_path).get_resource_lists()

        self.extreme_addons_path = extreme_addons_path

    def draw_requirement_files(self, layout, context=None, use_box=False):
        """Disegna le risorse richieste con un menu a tendina sicuro e indipendente."""

        if context is not None:
            box = layout.box()
            row = box.row(align=True)

            # Usiamo un operatore o una proprieta di classe pulita per evitare il WindowManager globale
            icon = 'DISCLOSURE_TRI_DOWN' if Draw.show_details_state else 'DISCLOSURE_TRI_RIGHT'

            # Creiamo un pulsante toggle pulito per gestire l'espansione senza registrazioni dinamiche illegali
            op = row.operator("exa.toggle_details", text="Installed Packages & Dependencies", icon=icon, emboss=False)

            if not Draw.show_details_state:
                return

            target_layout = box.column(align=True)
        else:
            target_layout = layout.box().column(align=True) if use_box else layout.column(align=True)

        target_layout.separator()

        if self.r_list.get("runtimes"):
            target_layout.label(text="Runtimes:", icon='FILE_SCRIPT')
            for runtime in self.r_list["runtimes"]:
                target_layout.label(text=f"  • {runtime}")
            target_layout.separator()

        if self.r_list.get("dependencies"):
            target_layout.label(text="Dependencies:", icon='PACKAGE')
            for dep in self.r_list["dependencies"]:
                target_layout.label(text=f"  • {dep}")
            target_layout.separator()

        if self.r_list.get("assets"):
            target_layout.label(text="Assets & AI Models:", icon='FILE_BACKUP')
            for asset in self.r_list["assets"]:
                target_layout.label(text=f"  • {asset}")

    def draw_exa_ai_core(self, context, layout):
        """Draws the AI Core interface with inline progress bar and collapsible details."""

        col = layout.column(align=True)
        from ..icons.interfaceicons import get_icon
        col.label(text="Exa AI Core Engine", icon_value=get_icon('exa_logo'))
        col.separator()

        wm = context.window_manager
        is_installing = getattr(wm, "exa_install_running", False)

        if is_installing:
            box_progress = col.box()
            box_progress.label(text="Installing Exa AI Core...", icon='PACKAGE')

            msg = getattr(wm, "exa_install_msg", "")
            if msg:
                box_progress.label(text=msg, icon='INFO')

            if hasattr(wm, "exa_install_progress"):
                box_progress.prop(wm, "exa_install_progress", text="Progress", slider=True)
            col.separator()

        service_ok = ServiceValidator(base_path=self.extreme_addons_path).is_installed()
        if not service_ok:
            box = col.box()
            box.alert = True
            box.label(text="The Exa AI Core is not installed. Install it to enable advanced tools and AI features.",
                      icon='ERROR')
            self.draw_requirement_files(box, context=context)

        else:
            box = col.box()
            box.label(text="The Exa AI Core is installed and active.", icon='CHECKMARK')
            self.draw_requirement_files(box, context=context)

        col.separator()
        row = col.row(align=True)
        row.scale_y = 2
        row.enabled = not is_installing

        if service_ok:
            text = "Reinstall Exa AI Core"
        else:
            text = "Install Exa AI Core"

        ops = row.operator("exa.install_microservice", text=text, icon='DOWNLOAD')
        ops.install_path = self.extreme_addons_path
        ops.options = 'INSTALL'

        if service_ok:
            ops = row.operator("exa.install_microservice", text="Uninstall Exa AI Core", icon='TRASH')
            ops.install_path = self.extreme_addons_path
            ops.options = 'UNINSTALL'


class EXAAICORE_OT_toggle_details(bpy.types.Operator):
    """Operatore leggero per gestire il click sul menu a tendina senza toccare i tipi globali"""
    bl_idname = "exa.toggle_details"
    bl_label = "Toggle Details"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        Draw.show_details_state = not Draw.show_details_state
        return {'FINISHED'}


