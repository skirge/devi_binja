from binaryninja import PluginCommand
from binaryninja import interaction
from binaryninja import InstructionTextTokenType
from binaryninja import demangle
from binaryninja import log
from binaryninja.variable import *
import json
import traceback
import os

class binja_devi():

    def __init__(self, bv):
        self.version = 0.2
        self.bv = bv
        self.call_cnt = 0
        self.load_virtual_calls()


    def load_virtual_calls(self):
        json_file = interaction.get_open_filename_input("Load virtual calls", "*.json")
        with open(json_file) as f:
            devi_json_data = json.load(f)
        if self.version < devi_json_data["deviVersion"]:
            print("[!] devi JSON file has a more recent version than IDA plugin!")
            print("[!] we try parsing anyway!")
        if self.version > devi_json_data["deviVersion"]:
            print("[!] Your devi_ida and devi_frida versions are out of sync. Update your devi_ida!")

        state = self.bv.begin_undo_actions()
        if self.version == devi_json_data["deviVersion"]:
            self.devirtualize_calls(devi_json_data["calls"], devi_json_data["modules"])
        elif devi_json_data["deviVersion"] == 0.1:
            self.devirtualize_calls_v01(devi_json_data["calls"])
        self.bv.commit_undo_actions(state)


    def devirtualize_calls(self, call_list, modules):
        binja_filename = os.path.basename(self.bv.file.original_filename).replace('.bndb','')

        for module in modules:
            if module["name"] == binja_filename:
                loaded_module = module
                break
        if loaded_module is None:
            print("[-] Module not found!")
            return 
        start = int(loaded_module["base"], 16)
        end = start + loaded_module["size"]

        print(f"[!] Adding virtual calls for {binja_filename}")

        for v_call in call_list:
            for call in v_call:
                if start <= int(call, 16) <= end:
                    print(call)

                    src = int(call, 16) - start
                    dst = int(v_call[call]) - start

                    src += self.bv.start
                    dst += self.bv.start

                    # print(hex(src))
                    # print(hex(dst))
                    funcs = self.bv.get_functions_containing(src)
                    if len(funcs) == 0:
                        log.log(1, "[-] Functions for address {} not found".format(src))
                        continue

                    self.caller = funcs[0]
                    self.caller.add_user_code_ref(src, dst)
                    self.add_call_comment(src, dst)
                    self.call_cnt += 1
        log.log(1, "Devirtualized {} calls".format(self.call_cnt))


    def devirtualize_calls_v01(self, call_list):
        for v_call in call_list:
            for call in v_call:
                to_addr = int(v_call[call])
                #print(hex(int(call)))
                #print(hex(to_addr))
                #print(hex(int(call)))
                #print(hex(to_addr))
                from_addr = int(call)
                self.caller = self.bv.get_functions_containing(from_addr)[0]
                self.caller.add_user_code_ref(from_addr, to_addr, from_arch=None)
                self.add_call_comment(from_addr, to_addr)
                self.call_cnt += 1
        log.log(1, "Devirtualized {} calls".format(self.call_cnt))

    def add_call_comment(self, from_addr, to_addr):
        to_func = self.bv.get_function_at(to_addr)
        if to_func is None or to_func.name is None:
            return
        _, name = demangle.demangle_gnu3(self.bv.arch, to_func.name)
        old_comment = self.caller.get_comment_at(from_addr)
        if name not in old_comment:
            self.caller.set_comment_at(from_addr, name + "\n" + old_comment)

PluginCommand.register("devi", "DEvirtualize VIrtual calls", binja_devi)
