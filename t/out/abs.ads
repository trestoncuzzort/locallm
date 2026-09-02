pragma Ada_2022;
with Ada.Numerics.Big_Numbers.Big_Integers;
use  Ada.Numerics.Big_Numbers.Big_Integers;
package T_Abs with SPARK_Mode is

   function F (X : Big_Integer) return Big_Integer
   with
     Post => (F'Result >= Big_Integer'(0))
       and then ((F'Result = X) or else (F'Result = (-X)));

   function F (X : Big_Integer) return Big_Integer is
     ((if (X < Big_Integer'(0)) then (-X) else X));

   --  The task at machine inputs with exact arithmetic: gnatprove's RAC
   --  cannot execute a Big_Integer expression, so F above can never carry a
   --  confirmed counterexample (header). Every magnitude here is bounded by
   --  construction, so a counterexample to F_Ce is a counterexample to the
   --  task itself.
   subtype Ce_Num is Long_Long_Long_Integer;
   subtype Ce_Int is Ce_Num range -2**40 .. 2**40;

   function F_Ce (X : Ce_Int) return Ce_Num
   with
     Post => (F_Ce'Result >= Ce_Num'(0))
       and then ((F_Ce'Result = X) or else (F_Ce'Result = (-X)));

   function F_Ce (X : Ce_Int) return Ce_Num is
     ((if (X < Ce_Num'(0)) then (-X) else X));

end T_Abs;
