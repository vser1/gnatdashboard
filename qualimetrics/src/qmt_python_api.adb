------------------------------------------------------------------------------
--                 Q u a l i m e t r i c s     D r i v er                   --
--                                                                          --
--                    Copyright (C) 2012-2013, AdaCore                      --
--                                                                          --
------------------------------------------------------------------------------
with Core_Properties;
with GNATCOLL.Scripts.Python; use GNATCOLL.Scripts.Python;
with GNATCOLL.VFS; use GNATCOLL.VFS;

package body Qmt_Python_Api is

   procedure Logs_Dir
     (Data : in out Callback_Data'Class;
      Command : String);

   procedure DB_File_Name
     (Data : in out Callback_Data'Class;
      Command : String);

   procedure User_Plugins_Dir
     (Data : in out Callback_Data'Class;
      Command : String);

   procedure Core_Plugins_Dir
     (Data : in out Callback_Data'Class;
      Command : String);

   procedure Logs_Dir
     (Data : in out Callback_Data'Class;
      Command : String)
   is
      Log_Dir : constant Virtual_File := Create_From_Dir
        (Create (Core_Properties.Project_Qmt_Dir_Name),
         Core_Properties.Project_Log_Dir_Name);
      pragma Unreferenced (Command);
   begin
      Set_Return_Value (Data, Log_Dir.Display_Full_Name);
   end Logs_Dir;

   procedure DB_File_Name
     (Data : in out Callback_Data'Class;
      Command : String) is
      pragma Unreferenced (Command);
   begin
      Set_Return_Value (Data, Core_Properties.DB_File_Name);
   end DB_File_Name;

   procedure Core_Plugins_Dir
     (Data : in out Callback_Data'Class;
      Command : String) is
      pragma Unreferenced (Command);
   begin
      Set_Return_Value
        (Data, Core_Properties.Qmt_Core_Plugin_Dir.Display_Full_Name);
   end Core_Plugins_Dir;

   procedure User_Plugins_Dir
     (Data : in out Callback_Data'Class;
      Command : String) is
      pragma Unreferenced (Command);
   begin
      Set_Return_Value
        (Data, Core_Properties.Qmt_User_Plugin_Dir.Display_Full_Name);
   end User_Plugins_Dir;

   procedure Initialise (Kernel : access GPS.CLI_Kernels.CLI_Kernel_Record) is
      pragma Unreferenced (Kernel);
   begin
      --  Register python module

      GNATCOLL.Scripts.Python.Register_Python_Scripting
        (Repo, "Qmt");
      Register_Standard_Classes (Qmt_Python_Api.Repo, "Console");

      --  Register commands
      GNATCOLL.Scripts.Register_Command
        (Repo, "user_plugin_dir", 0, 0, User_Plugins_Dir'Access);

      GNATCOLL.Scripts.Register_Command
        (Repo, "core_plugin_dir", 0, 0, Core_Plugins_Dir'Access);

      GNATCOLL.Scripts.Register_Command
        (Repo, "db_file_name", 0, 0, DB_File_Name'Access);

      GNATCOLL.Scripts.Register_Command
        (Repo, "logs_dir", 0, 0, Logs_Dir'Access);
   end Initialise;

end Qmt_Python_Api;
