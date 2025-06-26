import bpy
from bpy.utils import register_classes_factory

def dprint(message: str):
    """Prints in the system console if the addon's developer printing is ON"""
    prefs = bpy.context.preferences.addons[__package__].preferences
    if prefs.developer_print:
        print(f"[Reset Props]: {message}")


class ResetCustomPropertiesAddonPreferences(bpy.types.AddonPreferences):
    """Addon preferences"""
    bl_idname = __package__
    
    developer_print: bpy.props.BoolProperty(
        name="Enable Developer Prints in System Console",
        description=(
            "Menu Windows > Toggle. Helps with debugging issues in "
            "the addon."
        ),
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "developer_print")


class RESET_OT_custom_properties(bpy.types.Operator):
    """Reset custom properties to their default values"""
    bl_idname = "reset.custom_properties"
    bl_label = "Reset Custom Properties"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Reset custom properties to their default values"
    
    selection_only: bpy.props.BoolProperty(
        name="Selection Only",
        description="Reset custom properties only on selected bones",
        default=True
    )
    
    @classmethod
    def poll(cls, context):
        return(
            context.selected_objects and
            context.mode in ('OBJECT', 'POSE')
        )
    
    def list_custom_properties(self, source):
        """Make a list of user-defined custom properties from a source.
        Compatible with Blender 4.2+ by falling back to _RNA_UI if needed.
        """
        props = []
        rna_ui = source.get("_RNA_UI", {})

        dprint(f"Checking custom properties on '{source.name}'")

        for key, value in source.items():
            if key == "_RNA_UI":
                continue

            # Try modern Blender 4.4+ method first
            try:
                ui_data = source.id_properties_ui(key)
                if ui_data is not None:
                    props.append(key)
                    dprint(f"    Found user property: '{key}' (via UI data)")
                    continue
            except (TypeError, AttributeError):
                # Method doesn't exist or failed - will try fallback
                pass

            # Fallback for Blender 4.2 or legacy data
            if key in rna_ui:
                props.append(key)
                dprint(f"    Found user property: '{key}' (via _RNA_UI)")
            else:
                dprint(f"    Skipped API-defined property: '{key}'")

        dprint(f"Total user properties found: {len(props)}")
        return props
        
    def execute(self, context):
        reset_props_count = 0
        
        if context.mode == 'POSE':
            if self.selection_only:
                selection = context.selected_pose_bones
            else:
                armature = context.active_object
                selection = armature.pose.bones
                
            if not selection:
                self.report({'WARNING'}, "No bones selected")
                return {'CANCELLED'}
        else:
            selection = context.selected_objects
            if not selection:
                self.report({'WARNING'}, "No objects selected")
                return {'CANCELLED'}
            
        for item in selection:
            properties = self.list_custom_properties(item)
            
            if not properties:
                continue
            
            dprint(f"Processing properties on '{item.name}'")
            
            for prop_key in properties:
                current_value = item[prop_key]
                default_value = None
                
                # Try modern Blender 4.4+ method first
                try:
                    ui = item.id_properties_ui(prop_key)
                    
                    # Try different ways to get the default value
                    if hasattr(ui, 'as_dict'):
                        ui_dict = ui.as_dict()
                        default_value = ui_dict.get('default')
                        dprint(f"    Got default via as_dict(): {default_value}")
                    elif hasattr(ui, 'default'):
                        default_value = ui.default
                        dprint(f"    Got default via .default: {default_value}")
                        
                except (TypeError, AttributeError):
                    # Modern method failed, try fallback
                    pass
                
                # Fallback for Blender 4.2 or when modern method fails
                if default_value is None:
                    rna_ui = item.get('_RNA_UI', {})
                    prop_info = rna_ui.get(prop_key, {})
                    if 'default' in prop_info:
                        default_value = prop_info['default']
                        dprint(f"    Got default via _RNA_UI: {default_value}")
                    else:
                        dprint(f"    No default found for '{prop_key}', skipping")
                        continue

                if current_value != default_value:
                    item[prop_key] = default_value
                    reset_props_count += 1
                    dprint(f"    Reset '{prop_key}': {current_value} → {default_value}")
                else:
                    dprint(f"    '{prop_key}' already at default value")

        self.report({'INFO'}, f"Reset {reset_props_count} Custom Properties")
        
        # Force UI refresh to show updated values
        for area in bpy.context.screen.areas:
            area.tag_redraw()
            
        return {'FINISHED'}


class VIEW3D_MT_pose_reset_custom_properties(bpy.types.Menu):
    """Submenu for custom properties in pose mode"""
    bl_label = "Reset Custom Properties"
    bl_idname = "VIEW3D_MT_pose_reset_custom_properties"
    
    def draw(self, context):
        layout = self.layout
        
        op = layout.operator(
            "reset.custom_properties",
            text = "Selected Bones",
            icon = 'RESTRICT_SELECT_OFF'
        )
        op.selection_only = True
        
        op = layout.operator(
            "reset.custom_properties",
            text = "All Bones",
            icon = 'ARMATURE_DATA'
        )
        op.selection_only = False


def draw_menu_object(self, context):
    """Populates the object mode's menus"""
    if context.mode == 'OBJECT':
        layout = self.layout
        layout.operator(
            "reset.custom_properties",
            text = "Reset Custom Properties",
            icon = 'RECOVER_LAST'
        )


def draw_menu_pose(self, context):
    """Populates the pose mode's menus"""
    if context.mode == 'POSE':
        layout = self.layout
        layout.menu(
            "VIEW3D_MT_pose_reset_custom_properties",
            icon = 'RECOVER_LAST',
        )


classes = [
    ResetCustomPropertiesAddonPreferences,
    RESET_OT_custom_properties,
    VIEW3D_MT_pose_reset_custom_properties,
]

register_classes, unregister_classes = register_classes_factory(classes)


def register():
    register_classes()
    
    # Add menus
    bpy.types.VIEW3D_MT_object_clear.append(draw_menu_object)
    bpy.types.VIEW3D_MT_pose.prepend(draw_menu_pose)


def unregister():
    # Remove menus
    bpy.types.VIEW3D_MT_object_clear.remove(draw_menu_object)
    bpy.types.VIEW3D_MT_pose.remove(draw_menu_pose)
    
    unregister_classes()


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()