pragma Ada_2022;
with Ada.Numerics.Big_Numbers.Big_Integers;
use  Ada.Numerics.Big_Numbers.Big_Integers;
package T_Abs with SPARK_Mode is
   function F (X : Big_Integer) return Big_Integer is
     (-X)
   with
     Post => (F'Result >= 0)
     and then ((F'Result = X) or else (F'Result = (-X)));
end T_Abs;
