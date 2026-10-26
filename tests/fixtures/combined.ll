; ModuleID = 'combined.c'
source_filename = "combined.c"

declare i32 @get_buffer_limit()

define void @process(ptr %buf, i32 %n) {
entry:
  %limit = call i32 @get_buffer_limit()
  %cmp = icmp sle i32 %n, %limit
  br i1 %cmp, label %if.then, label %if.end

if.then:
  ret void

if.end:
  ret void
}
