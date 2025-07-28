"""Reset custom properties to their default values on objects and pose bones."""
# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from bpy.utils import register_classes_factory
from .bl_logger import logger


# def dprint(message: str):
#     """Prints in the system console if the addon's developer printing is ON"""
#     prefs = bpy.context.preferences.addons[__package__].preferences # type: ignore
#     if prefs.developer_print:
#         print(f"[Reset Props]: {message}")


class ResetCustomPropertiesAddonPreferences(bpy.types.AddonPreferences):
    """Addon preferences"""

    bl_idname = __package__ # type: ignore

    developer_print: bpy.props.BoolProperty(
        name="Enable Developer Log in System Console",
        description=(
            "Helps with debugging issues in the addon.\n"
            "Please use this for any bug report.\n"
            "Keep it disabled for better performances."
        ),
        default=False,
    )  # type: ignore

    def draw(self, context):
        """Draws the addon preferences UI"""
        _ = context # satisfy linter, not used here
        layout = self.layout
        row = layout.row()
        row.prop(self, "developer_print")
        row.operator("wm.console_toggle", icon="CONSOLE", text="")


# pylint: disable=invalid-name # Operator class names should be in uppercase
class RESET_OT_custom_properties(bpy.types.Operator):
    """Reset custom properties to their default values"""

    bl_idname = "reset.custom_properties"
    bl_label = "Reset Custom Properties"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Reset custom properties to their default values"

    selection_only: bpy.props.BoolProperty(
        name="Selection Only",
        description="Reset custom properties only on selected bones",
        default=True,
    )  # type: ignore

    @classmethod
    def poll(cls, context): # type: ignore
        """Operator availability check"""
        return context.selected_objects and context.mode in ("OBJECT", "POSE")

    def list_custom_properties(self, source):
        """Make a list of user-defined custom properties from a source.
        Compatible with Blender 4.2+ by falling back to _RNA_UI if needed.
        """
        props = []
        rna_ui = source.get("_RNA_UI", {})

        logger.debug("Checking custom properties on '%s'", source.name)

        for key in source.keys():
            # Skip "_RNA_UI" keys
            if key == "_RNA_UI":
                continue

            # Try modern Blender 4.4+ method first
            try:
                ui_data = source.id_properties_ui(key)
                if ui_data is not None:
                    props.append(key)
                    logger.debug(
                        "    Found user property: '%s' (via UI data)", key
                    )
                    continue
            except (TypeError, AttributeError) as exception:
                logger.warning(
                    "    Modern method failed:\n"
                    "                   %s\n"
                    "                   Fallback to _RNA_UI",
                    exception
                    )

            # Fallback for Blender 4.2 or legacy data
            if key in rna_ui:
                props.append(key)
                logger.info("    Found user property: '%s' (via _RNA_UI)", key)
            else:
                logger.debug(
                    "    Skipped API-defined property (via _RNA_UI): '%s'", key
                )

        logger.info("Total user properties found: %d", len(props))
        return props

    def execute(self, context): # type: ignore
        """Main execution"""
        reset_props_count = 0

        if context.mode == "POSE":
            if self.selection_only:
                selection = context.selected_pose_bones
            else:
                armature = context.active_object
                selection = armature.pose.bones # type: ignore

            if not selection:
                self.report({"WARNING"}, "No bones selected")
                return {"CANCELLED"}
        else:
            selection = context.selected_objects
            if not selection:
                self.report({"WARNING"}, "No objects selected")
                return {"CANCELLED"}

        for item in selection:
            properties = self.list_custom_properties(item)

            if not properties:
                continue

            logger.debug("Processing properties on '%s'", item.name)

            for prop_key in properties:
                current_value = item[prop_key]
                default_value = None

                # Try modern Blender 4.4+ method first
                try:
                    ui = item.id_properties_ui(prop_key)

                    # Try different ways to get the default value
                    if hasattr(ui, "as_dict"):
                        ui_dict = ui.as_dict()
                        default_value = ui_dict.get("default")
                        logger.debug(
                            "    Got default via as_dict(): %s",
                            str(default_value)
                        )
                    elif hasattr(ui, "default"):
                        default_value = ui.default
                        logger.debug(
                            "    Got default via .default: %s",
                            str(default_value)
                        )

                except (TypeError, AttributeError):
                    logger.debug("    Modern method failed, try fallback")

                # Fallback for Blender 4.2 or when modern method fails
                if default_value is None:
                    rna_ui = item.get("_RNA_UI", {})
                    prop_info = rna_ui.get(prop_key, {})
                    if "default" in prop_info:
                        default_value = prop_info["default"]
                        logger.debug(
                            "    Got default via _RNA_UI: %s", default_value
                        )
                    else:
                        logger.debug(
                            "    No default found for '%s', skipping", prop_key
                        )
                        continue

                if current_value != default_value:
                    item[prop_key] = default_value
                    reset_props_count += 1
                    logger.debug(
                        "    Reset '%s': %s → %s",
                        prop_key, current_value, default_value
                    )
                else:
                    logger.debug(
                        "    '%s' already at default value", prop_key
                    )

        self.report({"INFO"}, f"Reset {reset_props_count} Custom Properties")

        # Force UI refresh to show updated values
        for area in bpy.context.screen.areas:
            area.tag_redraw()
        if context.mode == "POSE":
            unique_armatures = {pb.id_data for pb in selection}
            for armature in unique_armatures:
                armature.update_tag()
        else:
            for obj in selection:
                obj.update_tag() # type: ignore

        return {"FINISHED"}


class VIEW3D_MT_pose_reset_custom_properties(bpy.types.Menu):
    """Submenu for custom properties in pose mode"""

    bl_label = "Reset Custom Properties"
    bl_idname = "VIEW3D_MT_pose_reset_custom_properties"

    def draw(self, context):
        """Custom menu drawing"""
        _ = context # satisfy linter, not used here
        layout = self.layout

        op = layout.operator(
            "reset.custom_properties", text="Selected Bones", icon="RESTRICT_SELECT_OFF"
        )
        op.selection_only = True # type: ignore

        op = layout.operator(
            "reset.custom_properties", text="All Bones", icon="ARMATURE_DATA"
        )
        op.selection_only = False # type: ignore


def draw_menu_object(self, context):
    """Populates the object mode's menus"""
    if context.mode == "OBJECT":
        layout = self.layout
        layout.operator(
            "reset.custom_properties", text="Custom Properties", icon="RECOVER_LAST"
        )


def draw_menu_pose(self, context):
    """Populates the pose mode's menus"""
    if context.mode == "POSE":
        layout = self.layout
        layout.menu(
            "VIEW3D_MT_pose_reset_custom_properties",
            icon="RECOVER_LAST",
        )


classes = [
    ResetCustomPropertiesAddonPreferences,
    RESET_OT_custom_properties,
    VIEW3D_MT_pose_reset_custom_properties,
]

register_classes, unregister_classes = register_classes_factory(classes)


def register():
    """Register operator classs then gui"""
    register_classes()

    bpy.types.VIEW3D_MT_object_clear.append(draw_menu_object)
    bpy.types.VIEW3D_MT_pose.prepend(draw_menu_pose)


def unregister():
    """Unregister operator gui then classes"""

    bpy.types.VIEW3D_MT_object_clear.remove(draw_menu_object)
    bpy.types.VIEW3D_MT_pose.remove(draw_menu_pose)

    unregister_classes()
