; ModuleID = 'ipcp_combined.c'
source_filename = "ipcp_combined.c"

define i32 @get_limit() {
entry:
  ret i32 256
}

define void @process(ptr %buf, i32 %n) {
entry:
  %limit = call i32 @get_limit()
  %cmp = icmp sgt i32 %n, %limit
  br i1 %cmp, label %if.then, label %if.end

if.then:
  ret void

if.end:
  ret void
}
